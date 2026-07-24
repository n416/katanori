#ifndef KATANORI_STATE_MACHINE_H
#define KATANORI_STATE_MACHINE_H

namespace katanori {

enum class RobotState {
    IDLE,
    LISTEN,
    THINK,
    SPEAK
};

enum class RobotEvent {
    WAKE_WORD,
    SPEECH_END,
    RESPONSE_READY,
    SPEECH_DONE,
    TIMEOUT
};

class StateMachine {
public:
    static constexpr float LISTEN_TIMEOUT = 10.0f;
    static constexpr float THINK_TIMEOUT = 15.0f;

    StateMachine();

    void update(float dt);
    void handleEvent(RobotEvent event);

    RobotState state() const { return state_; }
    float timeInState() const { return timeInState_; }

private:
    RobotState state_;
    float timeInState_;
};

} // namespace katanori

#endif // KATANORI_STATE_MACHINE_H