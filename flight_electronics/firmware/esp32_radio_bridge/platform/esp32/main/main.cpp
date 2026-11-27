// ESP-IDF entry point for the XIAO ESP32S3 + Wio-SX1262 radio bridge.
// Pins: flight_electronics/hardware/design.py RADIO['pins'].
// Build: idf.py set-target esp32s3 && idf.py build flash  (from platform/esp32)
#include <cstring>

#include "bridge.h"
#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "driver/uart.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

namespace {

constexpr int kSck = 7, kMiso = 8, kMosi = 9, kNss = 41, kReset = 42, kBusy = 40, kDio1 = 39, kRxEn = 38;
constexpr int kUartTx = 43, kUartRx = 44;
constexpr uart_port_t kUart = UART_NUM_1;
constexpr int kBaud = 921600;

class EspBus : public fe::Sx1262Bus {
 public:
  void init() {
    gpio_config_t out{};
    out.pin_bit_mask = (1ULL << kReset) | (1ULL << kRxEn);
    out.mode = GPIO_MODE_OUTPUT;
    gpio_config(&out);
    gpio_config_t in{};
    in.pin_bit_mask = (1ULL << kBusy) | (1ULL << kDio1);
    in.mode = GPIO_MODE_INPUT;
    gpio_config(&in);
    spi_bus_config_t bus{};
    bus.mosi_io_num = kMosi;
    bus.miso_io_num = kMiso;
    bus.sclk_io_num = kSck;
    bus.quadwp_io_num = -1;
    bus.quadhd_io_num = -1;
    bus.max_transfer_sz = 300;
    spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_CH_AUTO);
    spi_device_interface_config_t dev{};
    dev.clock_speed_hz = 8 * 1000 * 1000;
    dev.mode = 0;
    dev.spics_io_num = kNss;
    dev.queue_size = 1;
    spi_bus_add_device(SPI2_HOST, &dev, &spi_);
  }
  void transfer(const uint8_t* tx, uint8_t* rx, size_t len) override {
    const int64_t deadline = esp_timer_get_time() + 20000;
    while (gpio_get_level(static_cast<gpio_num_t>(kBusy)) && esp_timer_get_time() < deadline) {
    }
    spi_transaction_t t{};
    t.length = len * 8;
    t.tx_buffer = tx;
    t.rx_buffer = rx;
    spi_device_polling_transmit(spi_, &t);
  }
  bool dio1() override { return gpio_get_level(static_cast<gpio_num_t>(kDio1)) != 0; }
  void reset_pulse() override {
    gpio_set_level(static_cast<gpio_num_t>(kReset), 0);
    vTaskDelay(pdMS_TO_TICKS(2));
    gpio_set_level(static_cast<gpio_num_t>(kReset), 1);
    vTaskDelay(pdMS_TO_TICKS(10));
  }
  void rf_switch_rx(bool enable) override { gpio_set_level(static_cast<gpio_num_t>(kRxEn), enable ? 1 : 0); }
  uint32_t millis() override { return static_cast<uint32_t>(esp_timer_get_time() / 1000); }

 private:
  spi_device_handle_t spi_ = nullptr;
};

class EspUart : public fe::UartPort {
 public:
  void init() {
    uart_config_t cfg{};
    cfg.baud_rate = kBaud;
    cfg.data_bits = UART_DATA_8_BITS;
    cfg.parity = UART_PARITY_DISABLE;
    cfg.stop_bits = UART_STOP_BITS_1;
    cfg.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
    cfg.source_clk = UART_SCLK_DEFAULT;
    uart_driver_install(kUart, 1024, 1024, 0, nullptr, 0);
    uart_param_config(kUart, &cfg);
    uart_set_pin(kUart, kUartTx, kUartRx, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
  }
  void write(const uint8_t* data, size_t len) override { uart_write_bytes(kUart, data, len); }
  int read_byte() override {
    uint8_t c;
    return uart_read_bytes(kUart, &c, 1, 0) == 1 ? c : -1;
  }
};

EspBus bus;
EspUart uart;
fe::Sx1262 radio(bus);
fe::Bridge bridge(radio, bus, uart);

}  // namespace

extern "C" void app_main() {
  uart.init();
  bus.init();
  fe::LoraConfig cfg;  // 868.1 MHz, SF7, 125 kHz, 4/5, +22 dBm (EU 868 g1 sub-band)
  bridge.begin(cfg);
  while (true) {
    bridge.poll();
    vTaskDelay(1);  // 1 tick (1 ms with CONFIG_FREERTOS_HZ=1000)
  }
}
