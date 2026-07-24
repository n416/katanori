#include "Face.h"
#include <cmath>
#include <algorithm>

namespace katanori {

namespace {
constexpr float PI = 3.14159265358979323846f;

float lerp(float a, float b, float t) {
    return a + (b - a) * std::max(0.0f, std::min(1.0f, t));
}
} // namespace

Face::Face()
    : lastState_(RobotState::IDLE)
    , blinkTimer_(0.0f)
    , nextBlinkInterval_(4.0f)
    , isBlinking_(false)
    , blinkProgress_(0.0f)
    , idleGazeOffsetX_(0.0f)
    , idleGazeOffsetY_(0.0f)
    , gazeTimer_(0.0f)
    , nextGazeInterval_(2.5f)
    , transitionProgress_(1.0f)
    , thinkDotAngle_(0.0f)
    , micLevelSmooth_(0.0f)
{
    current_.eyes = {36.0f, 28.0f, 92.0f, 28.0f, 16.0f, 16.0f};
    current_.mouthWidth = 0.0f;
    current_.mouthHeight = 0.0f;
    current_.thinkAngle = 0.0f;
    transitionStartEyes_ = current_.eyes;
}

uint32_t Face::xorshift32() {
    static uint32_t seed = 0x12345678;
    seed ^= seed << 13;
    seed ^= seed >> 17;
    seed ^= seed << 5;
    return seed;
}

float Face::randomFloat(float minVal, float maxVal) {
    uint32_t val = xorshift32();
    float normalized = static_cast<float>(val) / 4294967295.0f;
    return minVal + normalized * (maxVal - minVal);
}

Face::EyeParams Face::calculateTargetEyes(RobotState state, float micLevel) {
    EyeParams target;
    switch (state) {
    case RobotState::IDLE:
        target.leftCx = 36.0f + idleGazeOffsetX_;
        target.leftCy = 28.0f + idleGazeOffsetY_;
        target.rightCx = 92.0f + idleGazeOffsetX_;
        target.rightCy = 28.0f + idleGazeOffsetY_;
        target.rx = 16.0f;
        target.ry = 16.0f;
        break;

    case RobotState::LISTEN: {
        float pulse = 1.0f + micLevel * 0.25f;
        target.leftCx = 36.0f;
        target.leftCy = 28.0f;
        target.rightCx = 92.0f;
        target.rightCy = 28.0f;
        target.rx = 19.0f * pulse;
        target.ry = 19.0f * pulse;
        break;
    }

    case RobotState::THINK:
        target.leftCx = 36.0f;
        target.leftCy = 22.0f;
        target.rightCx = 92.0f;
        target.rightCy = 22.0f;
        target.rx = 16.0f;
        target.ry = 6.0f;
        break;

    case RobotState::SPEAK:
        target.leftCx = 36.0f;
        target.leftCy = 26.0f;
        target.rightCx = 92.0f;
        target.rightCy = 26.0f;
        target.rx = 16.0f;
        target.ry = 16.0f;
        break;
    }
    return target;
}

void Face::update(float dt, RobotState state, float micLevel) {
    if (dt < 0.0f) dt = 0.0f;

    micLevelSmooth_ += (micLevel - micLevelSmooth_) * std::min(1.0f, dt * 12.0f);

    if (state != lastState_) {
        transitionStartEyes_ = current_.eyes;
        transitionProgress_ = 0.0f;
        lastState_ = state;
    }

    if (transitionProgress_ < 1.0f) {
        transitionProgress_ += dt / 0.25f;
        if (transitionProgress_ > 1.0f) {
            transitionProgress_ = 1.0f;
        }
    }

    if (state == RobotState::IDLE) {
        gazeTimer_ += dt;
        if (gazeTimer_ >= nextGazeInterval_) {
            gazeTimer_ = 0.0f;
            nextGazeInterval_ = randomFloat(2.0f, 4.0f);
            idleGazeOffsetX_ = randomFloat(-5.0f, 5.0f);
            idleGazeOffsetY_ = randomFloat(-2.0f, 2.0f);
        }
    } else {
        idleGazeOffsetX_ = 0.0f;
        idleGazeOffsetY_ = 0.0f;
    }

    blinkTimer_ += dt;
    if (!isBlinking_ && blinkTimer_ >= nextBlinkInterval_) {
        isBlinking_ = true;
        blinkProgress_ = 0.0f;
        blinkTimer_ = 0.0f;
        nextBlinkInterval_ = randomFloat(3.0f, 6.0f);
    }

    if (isBlinking_) {
        blinkProgress_ += dt / 0.15f;
        if (blinkProgress_ >= 1.0f) {
            isBlinking_ = false;
            blinkProgress_ = 0.0f;
        }
    }

    EyeParams targetEyes = calculateTargetEyes(state, micLevelSmooth_);
    float t = transitionProgress_;
    float smoothT = t * t * (3.0f - 2.0f * t);

    current_.eyes.leftCx = lerp(transitionStartEyes_.leftCx, targetEyes.leftCx, smoothT);
    current_.eyes.leftCy = lerp(transitionStartEyes_.leftCy, targetEyes.leftCy, smoothT);
    current_.eyes.rightCx = lerp(transitionStartEyes_.rightCx, targetEyes.rightCx, smoothT);
    current_.eyes.rightCy = lerp(transitionStartEyes_.rightCy, targetEyes.rightCy, smoothT);
    current_.eyes.rx = lerp(transitionStartEyes_.rx, targetEyes.rx, smoothT);
    current_.eyes.ry = lerp(transitionStartEyes_.ry, targetEyes.ry, smoothT);

    if (isBlinking_) {
        float blinkFactor = 1.0f - std::sin(blinkProgress_ * PI);
        current_.eyes.ry *= std::max(0.1f, blinkFactor);
    }

    if (state == RobotState::THINK) {
        thinkDotAngle_ += dt * 5.0f;
        if (thinkDotAngle_ > 2.0f * PI) {
            thinkDotAngle_ -= 2.0f * PI;
        }
    }

    if (state == RobotState::SPEAK) {
        current_.mouthWidth = 24.0f + micLevelSmooth_ * 16.0f;
        current_.mouthHeight = 2.0f + micLevelSmooth_ * 14.0f;
    } else {
        current_.mouthWidth = 0.0f;
        current_.mouthHeight = 0.0f;
    }
}

void Face::render(DisplayBuffer& buf) {
    buf.clear();

    int leftRx = static_cast<int>(current_.eyes.rx + 0.5f);
    int leftRy = static_cast<int>(current_.eyes.ry + 0.5f);
    int leftCx = static_cast<int>(current_.eyes.leftCx + 0.5f);
    int leftCy = static_cast<int>(current_.eyes.leftCy + 0.5f);

    int rightRx = static_cast<int>(current_.eyes.rx + 0.5f);
    int rightRy = static_cast<int>(current_.eyes.ry + 0.5f);
    int rightCx = static_cast<int>(current_.eyes.rightCx + 0.5f);
    int rightCy = static_cast<int>(current_.eyes.rightCy + 0.5f);

    for (int dy = -leftRy; dy <= leftRy; ++dy) {
        for (int dx = -leftRx; dx <= leftRx; ++dx) {
            if ((dx * dx * leftRy * leftRy + dy * dy * leftRx * leftRx) <= (leftRx * leftRx * leftRy * leftRy)) {
                buf.setPixel(leftCx + dx, leftCy + dy, true);
            }
        }
    }

    for (int dy = -rightRy; dy <= rightRy; ++dy) {
        for (int dx = -rightRx; dx <= rightRx; ++dx) {
            if ((dx * dx * rightRy * rightRy + dy * dy * rightRx * rightRx) <= (rightRx * rightRx * rightRy * rightRy)) {
                buf.setPixel(rightCx + dx, rightCy + dy, true);
            }
        }
    }

    if (lastState_ == RobotState::LISTEN) {
        int barW = static_cast<int>(micLevelSmooth_ * 40.0f);
        if (barW > 0) {
            int startX = 64 - barW / 2;
            buf.fillRect(startX, 56, barW, 4, true);
        }
    }

    if (lastState_ == RobotState::THINK) {
        int centerDotX = 118;
        int centerDotY = 10;
        int radius = 6;
        for (int i = 0; i < 3; ++i) {
            float angle = thinkDotAngle_ + i * (2.0f * PI / 3.0f);
            int dx = static_cast<int>(std::cos(angle) * radius);
            int dy = static_cast<int>(std::sin(angle) * radius);
            buf.fillCircle(centerDotX + dx, centerDotY + dy, 1, true);
        }
    }

    if (lastState_ == RobotState::SPEAK && current_.mouthHeight > 0.5f) {
        int mW = static_cast<int>(current_.mouthWidth + 0.5f);
        int mH = static_cast<int>(current_.mouthHeight + 0.5f);
        int mX = 64 - mW / 2;
        int mY = 52 - mH / 2;
        buf.fillRect(mX, mY, mW, mH, true);
    }
}

} // namespace katanori