#include "StateMachine.h"

namespace katanori {

StateMachine::StateMachine()
    : state_(RobotState::IDLE)
    , timeInState_(0.0f) {}

void StateMachine::update(float dt) {
    if (dt < 0.0f) return;
    timeInState_ += dt;

    if (state_ == RobotState::LISTEN && timeInState_ >= LISTEN_TIMEOUT) {
        handleEvent(RobotEvent::TIMEOUT);
    } else if (state_ == RobotState::THINK && timeInState_ >= THINK_TIMEOUT) {
        handleEvent(RobotEvent::TIMEOUT);
    }
}

void StateMachine::handleEvent(RobotEvent event) {
    switch (state_) {
    case RobotState::IDLE:
        if (event == RobotEvent::WAKE_WORD) {
            state_ = RobotState::LISTEN;
            timeInState_ = 0.0f;
        }
        break;

    case RobotState::LISTEN:
        if (event == RobotEvent::SPEECH_END) {
            state_ = RobotState::THINK;
            timeInState_ = 0.0f;
        } else if (event == RobotEvent::TIMEOUT) {
            state_ = RobotState::IDLE;
            timeInState_ = 0.0f;
        }
        break;

    case RobotState::THINK:
        if (event == RobotEvent::RESPONSE_READY) {
            state_ = RobotState::SPEAK;
            timeInState_ = 0.0f;
        } else if (event == RobotEvent::TIMEOUT) {
            state_ = RobotState::IDLE;
            timeInState_ = 0.0f;
        }
        break;

    case RobotState::SPEAK:
        if (event == RobotEvent::SPEECH_DONE) {
            state_ = RobotState::IDLE;
            timeInState_ = 0.0f;
        }
        break;
    }
}

} // namespace katanori