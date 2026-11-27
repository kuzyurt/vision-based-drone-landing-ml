#include "bridge.h"

#include <cstring>

namespace fe {

void Bridge::begin(const LoraConfig& cfg) {
  cfg_ = cfg;
  radio_.begin(cfg);
  radio_.clear_irq(0xFFFF);
  radio_.start_receive();
  mode_ = kModeRx;
  last_radio_activity_ = last_heartbeat_ = bus_.millis();
}

void Bridge::send_frame(uint8_t type, const uint8_t* payload, size_t len) {
  uint8_t out[200];
  const size_t n = frame_build(type, payload, len, out, sizeof out);
  if (n) uart_.write(out, n);
}

void Bridge::handle_irq() {
  const uint16_t irq = radio_.irq_status();
  if (!irq) return;
  radio_.clear_irq(irq);
  last_radio_activity_ = bus_.millis();
  if (irq & sx::kIrqTxDone) {
    ++counters_.tx_done;
    uint8_t seq[2] = {uint8_t(status_sequence_), uint8_t(status_sequence_ >> 8)};
    send_frame(kFrameTxDone, seq, 2);
    radio_.start_receive();
    mode_ = kModeRx;
    return;
  }
  if (irq & (sx::kIrqCrcErr | sx::kIrqHeaderErr)) {
    ++counters_.rx_bad;
    return;  // continuous RX keeps running
  }
  if (irq & sx::kIrqRxDone) {
    uint8_t packet[64];
    int16_t rssi = 0;
    int8_t snr = 0;
    const size_t len = radio_.read_packet(packet, sizeof packet, &rssi, &snr);
    Beacon beacon;
    if (!beacon_decode(packet, len, &beacon)) {
      ++counters_.rx_bad;
      return;
    }
    ++counters_.rx_ok;
    uint8_t payload[kBeaconSize + 7];
    std::memcpy(payload, packet, kBeaconSize);
    payload[kBeaconSize] = uint8_t(rssi);
    payload[kBeaconSize + 1] = uint8_t(uint16_t(rssi) >> 8);
    payload[kBeaconSize + 2] = uint8_t(snr);
    const uint32_t t = bus_.millis();
    for (int i = 0; i < 4; ++i) payload[kBeaconSize + 3 + i] = uint8_t(t >> (8 * i));
    send_frame(kFrameBeacon, payload, sizeof payload);
  }
}

void Bridge::handle_companion() {
  for (int c = uart_.read_byte(); c >= 0; c = uart_.read_byte()) {
    if (!parser_.push(uint8_t(c))) continue;
    ++counters_.frames_from_companion;
    if (parser_.type() == kFrameStatus && parser_.payload_len() <= sizeof pending_status_) {
      std::memcpy(pending_status_, parser_.payload(), parser_.payload_len());
      pending_len_ = parser_.payload_len();
    } else if (parser_.type() == kFramePing) {
      heartbeat(bus_.millis());
    }
  }
}

void Bridge::heartbeat(uint32_t now) {
  uint8_t p[17];
  const uint32_t values[4] = {now, counters_.rx_ok, counters_.rx_bad, counters_.tx_done};
  for (int v = 0; v < 4; ++v)
    for (int i = 0; i < 4; ++i) p[4 * v + i] = uint8_t(values[v] >> (8 * i));
  p[16] = mode_;
  send_frame(kFrameHeartbeat, p, sizeof p);
  last_heartbeat_ = now;
}

void Bridge::poll() {
  const uint32_t now = bus_.millis();
  handle_companion();
  if (bus_.dio1()) handle_irq();
  // Send a queued status packet only while not in the middle of a reception.
  if (pending_len_ && mode_ == kModeRx && !bus_.dio1()) {
    ++status_sequence_;
    radio_.transmit(pending_status_, pending_len_);
    pending_len_ = 0;
    mode_ = kModeTx;
  }
  if (now - last_heartbeat_ >= kHeartbeatMs) heartbeat(now);
  if (now - last_radio_activity_ >= kSilentReinitMs && mode_ == kModeRx) {
    // No IRQ for a long time: the radio may have locked up (brown-out, ESD). Re-initialise.
    ++counters_.reinit;
    begin(cfg_);
  }
}

}  // namespace fe
