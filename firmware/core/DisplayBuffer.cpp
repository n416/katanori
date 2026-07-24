#include "DisplayBuffer.h"
#include <algorithm>
#include <cstring>
#include <cmath>

namespace katanori {

DisplayBuffer::DisplayBuffer() {
    clear();
}

void DisplayBuffer::clear() {
    std::memset(buf_, 0, sizeof(buf_));
}

void DisplayBuffer::setPixel(int x, int y, bool on) {
    if (x < 0 || x >= W || y < 0 || y >= H) {
        return;
    }
    size_t index = static_cast<size_t>(y * (W / 8) + (x / 8));
    uint8_t bitMask = static_cast<uint8_t>(0x80 >> (x % 8));
    if (on) {
        buf_[index] |= bitMask;
    } else {
        buf_[index] &= static_cast<uint8_t>(~bitMask);
    }
}

bool DisplayBuffer::getPixel(int x, int y) const {
    if (x < 0 || x >= W || y < 0 || y >= H) {
        return false;
    }
    size_t index = static_cast<size_t>(y * (W / 8) + (x / 8));
    uint8_t bitMask = static_cast<uint8_t>(0x80 >> (x % 8));
    return (buf_[index] & bitMask) != 0;
}

void DisplayBuffer::drawHLine(int x, int y, int w, bool on) {
    if (y < 0 || y >= H || w <= 0) return;
    int startX = std::max(0, x);
    int endX = std::min(W - 1, x + w - 1);
    for (int ix = startX; ix <= endX; ++ix) {
        setPixel(ix, y, on);
    }
}

void DisplayBuffer::drawVLine(int x, int y, int h, bool on) {
    if (x < 0 || x >= W || h <= 0) return;
    int startY = std::max(0, y);
    int endY = std::min(H - 1, y + h - 1);
    for (int iy = startY; iy <= endY; ++iy) {
        setPixel(x, iy, on);
    }
}

void DisplayBuffer::fillRect(int x, int y, int w, int h, bool on) {
    if (w <= 0 || h <= 0) return;
    int startY = std::max(0, y);
    int endY = std::min(H - 1, y + h - 1);
    for (int iy = startY; iy <= endY; ++iy) {
        drawHLine(x, iy, w, on);
    }
}

void DisplayBuffer::drawRect(int x, int y, int w, int h, bool on) {
    if (w <= 0 || h <= 0) return;
    drawHLine(x, y, w, on);
    drawHLine(x, y + h - 1, w, on);
    drawVLine(x, y, h, on);
    drawVLine(x + w - 1, y, h, on);
}

void DisplayBuffer::fillCircle(int cx, int cy, int r, bool on) {
    if (r < 0) return;
    if (r == 0) {
        setPixel(cx, cy, on);
        return;
    }
    for (int dy = -r; dy <= r; ++dy) {
        int py = cy + dy;
        if (py < 0 || py >= H) continue;
        int dxLimit = static_cast<int>(std::sqrt(r * r - dy * dy));
        drawHLine(cx - dxLimit, py, dxLimit * 2 + 1, on);
    }
}

} // namespace katanori