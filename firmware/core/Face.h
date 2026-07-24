#ifndef KATANORI_FACE_H
#define KATANORI_FACE_H

#include "DisplayBuffer.h"
#include "StateMachine.h"
#include <cstdint>

namespace katanori {

class Face {
public:
    Face();

    void update(float dt, RobotState state, float micLevel);
    void render(DisplayBuffer& buf);

private:
    struct EyeParams {
        float leftCx, leftCy;
        float rightCx, rightCy;
        float rx, ry;
    };

    struct FaceState {
        EyeParams eyes;
        float mouthWidth;
        float mouthHeight;
        float thinkAngle;
    };

    uint32_t xorshift32();
    float randomFloat(float minVal, float maxVal);
    EyeParams calculateTargetEyes(RobotState state, float micLevel);

    FaceState current_;
    RobotState lastState_;

    float blinkTimer_;
    float nextBlinkInterval_;
    bool isBlinking_;
    float blinkProgress_;

    float idleGazeOffsetX_;
    float idleGazeOffsetY_;
    float gazeTimer_;
    float nextGazeInterval_;

    float transitionProgress_;
    EyeParams transitionStartEyes_;

    float thinkDotAngle_;
    float micLevelSmooth_;
};

} // namespace katanori

#endif // KATANORI_FACE_H