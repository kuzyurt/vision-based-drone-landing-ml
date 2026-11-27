#include "protocol.h"

#include <cstring>

namespace fe {

uint16_t crc16_ccitt(const uint8_t* data, size_t len, uint16_t crc) {
  for (size_t i = 0; i < len; ++i) {
    crc ^= static_cast<uint16_t>(data[i]) << 8;
    for (int b = 0; b < 8; ++b) crc = (crc & 0x8000) ? static_cast<uint16_t>((crc << 1) ^ 0x1021) : static_cast<uint16_t>(crc << 1);
  }
  return crc;
}

static void put16(uint8_t* p, uint16_t v) { p[0] = v & 0xFF; p[1] = v >> 8; }
static void put32(uint8_t* p, uint32_t v) { for (int i = 0; i < 4; ++i) p[i] = (v >> (8 * i)) & 0xFF; }
static uint16_t get16(const uint8_t* p) { return static_cast<uint16_t>(p[0] | (p[1] << 8)); }
static uint32_t get32(const uint8_t* p) {
  return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) |
         (static_cast<uint32_t>(p[2]) << 16) | (static_cast<uint32_t>(p[3]) << 24);
}

size_t beacon_encode(const Beacon& in, uint8_t* out) {
  out[0] = 'B'; out[1] = 'T'; out[2] = kBeaconVersion;
  put16(out + 3, in.sequence);
  put32(out + 5, in.boat_time_ms);
  put32(out + 9, static_cast<uint32_t>(in.east_cm));
  put32(out + 13, static_cast<uint32_t>(in.north_cm));
  put32(out + 17, static_cast<uint32_t>(in.up_cm));
  put16(out + 21, static_cast<uint16_t>(in.ve_cm_s));
  put16(out + 23, static_cast<uint16_t>(in.vn_cm_s));
  put16(out + 25, static_cast<uint16_t>(in.vu_cm_s));
  out[27] = in.flags;
  put16(out + 28, in.position_sigma_cm);
  put16(out + 30, crc16_ccitt(out, 30));
  return kBeaconSize;
}

bool beacon_decode(const uint8_t* d, size_t len, Beacon* out) {
  if (len != kBeaconSize || d[0] != 'B' || d[1] != 'T' || d[2] != kBeaconVersion) return false;
  if (crc16_ccitt(d, 30) != get16(d + 30)) return false;
  out->sequence = get16(d + 3);
  out->boat_time_ms = get32(d + 5);
  out->east_cm = static_cast<int32_t>(get32(d + 9));
  out->north_cm = static_cast<int32_t>(get32(d + 13));
  out->up_cm = static_cast<int32_t>(get32(d + 17));
  out->ve_cm_s = static_cast<int16_t>(get16(d + 21));
  out->vn_cm_s = static_cast<int16_t>(get16(d + 23));
  out->vu_cm_s = static_cast<int16_t>(get16(d + 25));
  out->flags = d[27];
  out->position_sigma_cm = get16(d + 28);
  return true;
}

size_t cobs_encode(const uint8_t* in, size_t len, uint8_t* out) {
  size_t read = 0, write = 1, code_index = 0;
  uint8_t code = 1;
  while (read < len) {
    if (in[read] == 0) {
      out[code_index] = code;
      code = 1;
      code_index = write++;
      ++read;
    } else {
      out[write++] = in[read++];
      if (++code == 0xFF) {
        out[code_index] = code;
        code = 1;
        code_index = write++;
      }
    }
  }
  out[code_index] = code;
  return write;
}

size_t cobs_decode(const uint8_t* in, size_t len, uint8_t* out) {
  size_t read = 0, write = 0;
  while (read < len) {
    const uint8_t code = in[read++];
    if (code == 0 || read + code - 1 > len) return 0;
    for (uint8_t i = 1; i < code; ++i) {
      if (in[read] == 0) return 0;
      out[write++] = in[read++];
    }
    if (code != 0xFF && read < len) out[write++] = 0;
  }
  return write;
}

size_t frame_build(uint8_t type, const uint8_t* payload, size_t len, uint8_t* out, size_t cap) {
  uint8_t plain[160];
  if (len + 3 > sizeof(plain) || cap < len + 3 + (len + 3) / 254 + 2) return 0;
  plain[0] = type;
  if (len) std::memcpy(plain + 1, payload, len);
  uint16_t crc = crc16_ccitt(plain, len + 1);
  plain[len + 1] = crc >> 8;
  plain[len + 2] = crc & 0xFF;
  size_t n = cobs_encode(plain, len + 3, out);
  out[n++] = 0;
  return n;
}

bool FrameParser::push(uint8_t byte) {
  if (byte != 0) {
    if (raw_len_ < sizeof(raw_)) raw_[raw_len_++] = byte;
    else { raw_len_ = 0; ++errors_; }
    return false;
  }
  size_t n = raw_len_ ? cobs_decode(raw_, raw_len_, decoded_) : 0;
  raw_len_ = 0;
  if (n < 3) { if (n) ++errors_; return false; }
  uint16_t crc = static_cast<uint16_t>((decoded_[n - 2] << 8) | decoded_[n - 1]);
  if (crc16_ccitt(decoded_, n - 2) != crc) { ++errors_; return false; }
  type_ = decoded_[0];
  payload_len_ = n - 3;
  return true;
}

}  // namespace fe
