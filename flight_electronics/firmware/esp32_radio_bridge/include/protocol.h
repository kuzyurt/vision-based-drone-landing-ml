// Wire formats shared by the boat transmitter, this firmware and the companion computer.
//
// Boat beacon (LoRa payload, 32 bytes, little-endian):
//   0  'B' 'T'          magic
//   2  u8  version (1)
//   3  u16 sequence
//   5  u32 boat_time_ms
//   9  i32 east_cm, i32 north_cm, i32 up_cm      position in the mission ENU frame
//  21  i16 ve_cm_s, i16 vn_cm_s, i16 vu_cm_s     velocity
//  27  u8  flags (bit0 dock ready, bit1 dock status valid)
//  28  u16 position_sigma_cm
//  30  u16 CRC-16/CCITT-FALSE over bytes 0..29
//
// Serial link to the companion computer: COBS-encoded frames ended by 0x00.
// Decoded frame: u8 type, payload, u16 CRC-16/CCITT-FALSE (big-endian) over type+payload.
#pragma once
#include <cstddef>
#include <cstdint>

namespace fe {

constexpr size_t kBeaconSize = 32;
constexpr uint8_t kBeaconVersion = 1;

enum FrameType : uint8_t {
  kFrameBeacon = 0x01,     // beacon bytes + i16 rssi_dbm_x10 + i8 snr_db_x4 + u32 rx_time_ms
  kFrameHeartbeat = 0x02,  // u32 uptime_ms, u32 rx_ok, u32 rx_bad, u32 tx_done, u8 radio_mode
  kFrameTxDone = 0x03,     // u16 sequence of the status packet that left the antenna
  kFrameStatus = 0x10,     // companion -> radio: status payload to send to the boat (<= 32 bytes)
  kFramePing = 0x11,       // companion -> radio
};

struct Beacon {
  uint16_t sequence;
  uint32_t boat_time_ms;
  int32_t east_cm, north_cm, up_cm;
  int16_t ve_cm_s, vn_cm_s, vu_cm_s;
  uint8_t flags;
  uint16_t position_sigma_cm;
};

uint16_t crc16_ccitt(const uint8_t* data, size_t len, uint16_t crc = 0xFFFF);
bool beacon_decode(const uint8_t* data, size_t len, Beacon* out);
size_t beacon_encode(const Beacon& in, uint8_t* out);

// COBS. Encoded size <= len + len/254 + 1. Returns encoded length (no trailing zero).
size_t cobs_encode(const uint8_t* in, size_t len, uint8_t* out);
// Returns decoded length, or 0 on malformed input.
size_t cobs_decode(const uint8_t* in, size_t len, uint8_t* out);

// Builds type+payload+crc, COBS encodes, appends 0x00. Returns bytes written.
size_t frame_build(uint8_t type, const uint8_t* payload, size_t len, uint8_t* out, size_t cap);

// Incremental frame parser for the receive side.
class FrameParser {
 public:
  // Feed one byte. Returns true when a complete valid frame is available.
  bool push(uint8_t byte);
  uint8_t type() const { return type_; }
  const uint8_t* payload() const { return decoded_ + 1; }
  size_t payload_len() const { return payload_len_; }
  uint32_t errors() const { return errors_; }

 private:
  uint8_t raw_[160];
  uint8_t decoded_[160];
  size_t raw_len_ = 0;
  size_t payload_len_ = 0;
  uint8_t type_ = 0;
  uint32_t errors_ = 0;
};

}  // namespace fe
