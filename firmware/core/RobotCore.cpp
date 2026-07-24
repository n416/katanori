#include "RobotCore.h"

namespace katanori {

RobotCore::RobotCore(IHal& hal)
    : hal_(hal)
    , lastMillis_(hal.millis())
{
}

void RobotCore::tick() {
    uint32_t currentMillis = hal_.millis();
    uint32_t elapsedMillis = currentMillis - lastMillis_;
    lastMillis_ = currentMillis;

    float dt = static_cast<float>(elapsedMillis) / 1000.0f;
    if (dt > 0.2f) {
        dt = 0.2f;
    }

    float micLevel = hal_.getMicLevel();

    stateMachine_.update(dt);
    face_.update(dt, stateMachine_.state(), micLevel);

    face_.render(buffer_);
    hal_.flushDisplay(buffer_.data());
}

void RobotCore::injectEvent(RobotEvent event) {
    stateMachine_.handleEvent(event);
}

} // namespace katanori