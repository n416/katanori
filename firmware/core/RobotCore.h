#ifndef KATANORI_ROBOT_CORE_H
#define KATANORI_ROBOT_CORE_H

#include "IHal.h"
#include "DisplayBuffer.h"
#include "StateMachine.h"
#include "Face.h"
#include <cstdint>

namespace katanori {

class RobotCore {
public:
    explicit RobotCore(IHal& hal);

    void tick();
    void injectEvent(RobotEvent event);

    RobotState state() const { return stateMachine_.state(); }
    const DisplayBuffer& displayBuffer() const { return buffer_; }

private:
    IHal& hal_;
    DisplayBuffer buffer_;
    StateMachine stateMachine_;
    Face face_;
    uint32_t lastMillis_;
};

} // namespace katanori

#endif // KATANORI_ROBOT_CORE_H