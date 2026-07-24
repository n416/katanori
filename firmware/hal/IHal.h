#ifndef KATANORI_IHAL_H
#define KATANORI_IHAL_H

#include <cstdint>

namespace katanori {

struct IHal {
    virtual ~IHal() = default;
    virtual uint32_t millis() = 0;
    virtual float getMicLevel() = 0;                  // 0.0..1.0
    virtual void flushDisplay(const uint8_t* fb) = 0; // DisplayBuffer::data() 形式
    virtual void log(const char* msg) = 0;
};

} // namespace katanori

#endif // KATANORI_IHAL_H