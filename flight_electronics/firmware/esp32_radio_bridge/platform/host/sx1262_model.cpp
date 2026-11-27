#include "sx1262_model.h"

#include <cmath>

namespace fe {

void Sx1262Model::reset_pulse() {
  mode_ = 1;
  irq_ = 0;
  irq_mask_dio1_ = 0;
  packet_type_ = 0;
}

void Sx1262Model::advance() {
  if (mode_ == 3 && *clock_ >= tx_end_ms_) {
    transmitted_.push_back(tx_payload_);
    irq_ |= sx::kIrqTxDone;
    mode_ = 1;  // returns to standby after TxDone
  }
}

void Sx1262Model::deliver(const uint8_t* data, size_t len, float rssi_dbm, float snr_db, bool crc_ok) {
  advance();
  if (mode_ != 2 || !rxen_ || len > 255) return;  // not listening: the packet is lost
  if (!crc_ok) { irq_ |= sx::kIrqCrcErr; return; }
  std::memcpy(buffer_, data, len);
  rx_len_ = static_cast<uint8_t>(len);
  rssi_raw_ = static_cast<uint8_t>(std::lround(-2.0f * rssi_dbm));
  snr_raw_ = static_cast<int8_t>(std::lround(4.0f * snr_db));
  irq_ |= sx::kIrqRxDone;
}

bool Sx1262Model::take_transmitted(std::vector<uint8_t>* out) {
  advance();
  if (transmitted_.empty()) return false;
  *out = transmitted_.front();
  transmitted_.pop_front();
  return true;
}

void Sx1262Model::transfer(const uint8_t* tx, uint8_t* rx, size_t len) {
  advance();
  ++commands_;
  std::memset(rx, 0, len);
  if (len == 0) return;
  const uint8_t status = static_cast<uint8_t>((mode_ == 2 ? 0x5 : mode_ == 3 ? 0x6 : 0x2) << 4);
  for (size_t i = 0; i < len; ++i) rx[i] = status;
  switch (tx[0]) {
    case sx::kSetStandby: mode_ = 1; break;
    case sx::kSetSleep: mode_ = 0; break;
    case sx::kSetPacketType: packet_type_ = tx[1]; break;
    case sx::kSetRfFrequency: frf_ = (uint32_t(tx[1]) << 24) | (uint32_t(tx[2]) << 16) | (uint32_t(tx[3]) << 8) | tx[4]; break;
    case sx::kSetTxParams: power_ = static_cast<int8_t>(tx[1]); break;
    case sx::kSetModulationParams: sf_ = tx[1]; bw_code_ = tx[2]; cr_ = tx[3]; break;
    case sx::kSetPacketParams:
      preamble_ = static_cast<uint16_t>((tx[1] << 8) | tx[2]);
      payload_len_ = tx[4];
      break;
    case sx::kSetDioIrqParams: irq_mask_dio1_ = static_cast<uint16_t>((tx[3] << 8) | tx[4]); break;
    case sx::kClearIrqStatus: irq_ &= static_cast<uint16_t>(~((tx[1] << 8) | tx[2])); break;
    case sx::kGetIrqStatus: if (len >= 4) { rx[2] = irq_ >> 8; rx[3] = irq_ & 0xFF; } break;
    case sx::kWriteBuffer: std::memcpy(buffer_ + tx[1], tx + 2, len - 2); break;
    case sx::kGetRxBufferStatus: if (len >= 4) { rx[2] = rx_len_; rx[3] = 0; } break;
    case sx::kReadBuffer:
      for (size_t i = 3; i < len; ++i) rx[i] = buffer_[(tx[1] + i - 3) & 0xFF];
      break;
    case sx::kGetPacketStatus: if (len >= 5) { rx[2] = rssi_raw_; rx[3] = uint8_t(snr_raw_); rx[4] = rssi_raw_; } break;
    case sx::kSetRx: mode_ = 2; break;
    case sx::kSetTx: {
      LoraConfig cfg;
      cfg.spreading_factor = sf_;
      cfg.bandwidth_hz = bw_code_ == 3 ? 62500 : bw_code_ == 5 ? 250000 : bw_code_ == 6 ? 500000 : 125000;
      cfg.coding_rate = static_cast<uint8_t>(cr_ + 4);
      cfg.preamble = preamble_;
      tx_payload_.assign(buffer_, buffer_ + payload_len_);
      tx_end_ms_ = *clock_ + (lora_time_on_air_us(cfg, payload_len_) + 999) / 1000;
      mode_ = 3;
      break;
    }
    default: break;  // calibration, regulator, PA config, TCXO, registers: accepted
  }
}

}  // namespace fe
