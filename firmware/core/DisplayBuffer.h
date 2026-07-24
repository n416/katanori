#ifndef KATANORI_DISPLAY_BUFFER_H
#define KATANORI_DISPLAY_BUFFER_H

#include <cstdint>
#include <cstddef>

namespace katanori {

/**
 * @brief 128x64 モノクロ (1bpp) ディスプレイバッファクラス
 * 内部バッファ構造:
 * - 全 1024 バイト (128 * 64 / 8)
 * - 行優先 (Row-major) 配置
 * - 各バイトは横8ピクセルを表す
 * - MSB (0x80) が左側ピクセル、LSB (0x01) が右側ピクセル
 */
class DisplayBuffer {
public:
    static constexpr int W = 128;
    static constexpr int H = 64;
    static constexpr size_t BUFFER_SIZE = static_cast<size_t>(W * H / 8);

    DisplayBuffer();

    void clear();
    void setPixel(int x, int y, bool on);
    bool getPixel(int x, int y) const;

    void drawHLine(int x, int y, int w, bool on);
    void drawVLine(int x, int y, int h, bool on);
    void fillRect(int x, int y, int w, int h, bool on);
    void drawRect(int x, int y, int w, int h, bool on);
    void fillCircle(int cx, int cy, int r, bool on);

    const uint8_t* data() const { return buf_; }
    uint8_t* data() { return buf_; }

private:
    uint8_t buf_[BUFFER_SIZE];
};

} // namespace katanori

#endif // KATANORI_DISPLAY_BUFFER_H