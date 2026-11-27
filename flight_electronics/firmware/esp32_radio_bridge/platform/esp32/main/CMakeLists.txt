idf_component_register(
    SRCS "main.cpp" "../../../src/protocol.cpp" "../../../src/sx1262.cpp" "../../../src/bridge.cpp"
    INCLUDE_DIRS "../../../include"
    REQUIRES driver esp_timer)
