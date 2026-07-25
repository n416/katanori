#include <windows.h>
#include <mmsystem.h>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <algorithm>
#include <thread>
#include <iostream>
#include <string>
#include "IHal.h"
#include "RobotCore.h"

namespace {

constexpr UINT WM_APP_CMD_SPEAK_START = WM_APP + 1;
constexpr UINT WM_APP_CMD_SPEAK_END   = WM_APP + 2;

HWND g_hwnd = NULL;

constexpr int SCALE = 8;
constexpr int DISP_W = 128;
constexpr int DISP_H = 64;
constexpr int WIN_W = DISP_W * SCALE;
constexpr int WIN_H = DISP_H * SCALE;

// 色定義 (0x00BBGGRR)
constexpr DWORD COLOR_ON  = RGB(0, 220, 255); // 点灯: シアン系
constexpr DWORD COLOR_OFF = RGB(10, 15, 30);   // 消灯: 深い紺

class Win32Hal : public katanori::IHal {
public:
    Win32Hal()
        : micPressed_(false)
        , currentMicLevel_(0.0f)
        , hwnd_(NULL)
        , hWaveIn_(NULL)
    {
        std::memset(pixelBuffer_, 0, sizeof(pixelBuffer_));
        bmi_.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
        bmi_.bmiHeader.biWidth = DISP_W;
        bmi_.bmiHeader.biHeight = -DISP_H; // トップダウン
        bmi_.bmiHeader.biPlanes = 1;
        bmi_.bmiHeader.biBitCount = 32;
        bmi_.bmiHeader.biCompression = BI_RGB;
        
        startAudioCapture();
    }
    
    ~Win32Hal() {
        stopAudioCapture();
    }

    void setHwnd(HWND hwnd) { hwnd_ = hwnd; }
    void setMicPressed(bool pressed) { micPressed_ = pressed; }

    uint32_t millis() override {
        return static_cast<uint32_t>(GetTickCount());
    }

    float getMicLevel() override {
        float rawMic = processAudioBuffer();
        
        if (micPressed_) {
            float randVal = static_cast<float>(std::rand()) / RAND_MAX;
            currentMicLevel_ = 0.2f + randVal * 0.8f;
        } else if (rawMic >= 0.0f) {
            currentMicLevel_ = rawMic;
        } else {
            currentMicLevel_ *= 0.85f; // 減衰
            if (currentMicLevel_ < 0.01f) {
                currentMicLevel_ = 0.0f;
            }
        }
        return currentMicLevel_;
    }

    void flushDisplay(const uint8_t* fb) override {
        for (int y = 0; y < DISP_H; ++y) {
            for (int x = 0; x < DISP_W; ++x) {
                size_t byteIdx = static_cast<size_t>(y * (DISP_W / 8) + (x / 8));
                uint8_t bitMask = static_cast<uint8_t>(0x80 >> (x % 8));
                bool isOn = (fb[byteIdx] & bitMask) != 0;
                pixelBuffer_[y * DISP_W + x] = isOn ? COLOR_ON : COLOR_OFF;
            }
        }

        if (hwnd_) {
            HDC hdc = GetDC(hwnd_);
            if (hdc) {
                StretchDIBits(
                    hdc,
                    0, 0, WIN_W, WIN_H,
                    0, 0, DISP_W, DISP_H,
                    pixelBuffer_,
                    &bmi_,
                    DIB_RGB_COLORS,
                    SRCCOPY
                );
                ReleaseDC(hwnd_, hdc);
            }
        }
    }

    void log(const char* msg) override {
        std::printf("[HAL LOG] %s\n", msg);
        std::fflush(stdout);
    }

private:
    bool micPressed_;
    float currentMicLevel_;
    HWND hwnd_;
    DWORD pixelBuffer_[DISP_W * DISP_H];
    BITMAPINFO bmi_;

    HWAVEIN hWaveIn_;
    WAVEHDR waveHdr_[2];
    int16_t audioBuf_[2][2048];

    void startAudioCapture() {
        WAVEFORMATEX wfx = {};
        wfx.wFormatTag = WAVE_FORMAT_PCM;
        wfx.nChannels = 1;
        wfx.nSamplesPerSec = 44100; // 一般的なCD音質に変更
        wfx.wBitsPerSample = 16;
        wfx.nBlockAlign = (wfx.nChannels * wfx.wBitsPerSample) / 8;
        wfx.nAvgBytesPerSec = wfx.nSamplesPerSec * wfx.nBlockAlign;

        MMRESULT res = waveInOpen(&hWaveIn_, WAVE_MAPPER, &wfx, 0, 0, CALLBACK_NULL);
        if (res != MMSYSERR_NOERROR) {
            // 44.1kHzがダメなら48kHzを試す
            wfx.nSamplesPerSec = 48000;
            wfx.nAvgBytesPerSec = wfx.nSamplesPerSec * wfx.nBlockAlign;
            res = waveInOpen(&hWaveIn_, WAVE_MAPPER, &wfx, 0, 0, CALLBACK_NULL);
        }

        if (res != MMSYSERR_NOERROR) {
            std::printf("[MIC ERROR] Failed to open microphone. Error code: %u\n", res);
            std::printf("[MIC ERROR] Check Windows Privacy settings for Microphone access.\n");
            return;
        }
        std::printf("[MIC] Microphone opened successfully at %u Hz.\n", wfx.nSamplesPerSec);

        for (int i = 0; i < 2; ++i) {
            std::memset(&waveHdr_[i], 0, sizeof(WAVEHDR));
            waveHdr_[i].lpData = reinterpret_cast<LPSTR>(audioBuf_[i]);
            waveHdr_[i].dwBufferLength = sizeof(audioBuf_[i]);
            waveInPrepareHeader(hWaveIn_, &waveHdr_[i], sizeof(WAVEHDR));
            waveInAddBuffer(hWaveIn_, &waveHdr_[i], sizeof(WAVEHDR));
        }
        waveInStart(hWaveIn_);
    }

    void stopAudioCapture() {
        if (hWaveIn_) {
            waveInStop(hWaveIn_);
            waveInReset(hWaveIn_);
            for (int i = 0; i < 2; ++i) {
                waveInUnprepareHeader(hWaveIn_, &waveHdr_[i], sizeof(WAVEHDR));
            }
            waveInClose(hWaveIn_);
            hWaveIn_ = NULL;
        }
    }

    float processAudioBuffer() {
        if (!hWaveIn_) return -1.0f;

        float maxAmp = -1.0f;
        for (int i = 0; i < 2; ++i) {
            if (waveHdr_[i].dwFlags & WHDR_DONE) {
                int samples = waveHdr_[i].dwBytesRecorded / sizeof(int16_t);
                for (int j = 0; j < samples; ++j) {
                    float amp = std::abs(static_cast<float>(audioBuf_[i][j])) / 32768.0f;
                    if (amp > maxAmp) maxAmp = amp;
                }
                waveHdr_[i].dwFlags &= ~WHDR_DONE;
                waveInAddBuffer(hWaveIn_, &waveHdr_[i], sizeof(WAVEHDR));
            }
        }
        
        if (maxAmp >= 0.0f) {
            maxAmp *= 10.0f; // ゲインをさらに上げる
            if (maxAmp > 1.0f) maxAmp = 1.0f;
        }
        return maxAmp;
    }
};

Win32Hal g_hal;
katanori::RobotCore g_robot(g_hal);
const char* g_stateNames[] = { "IDLE", "LISTEN", "THINK", "SPEAK" };

void StdinMonitorThread() {
    std::string line;
    // 標準入力(stdin)から行を読み取り続ける
    while (std::getline(std::cin, line)) {
        if (line.find("CMD:SPEAK_START") != std::string::npos) {
            if (g_hwnd) PostMessageA(g_hwnd, WM_APP_CMD_SPEAK_START, 0, 0);
        }
        else if (line.find("CMD:SPEAK_END") != std::string::npos) {
            if (g_hwnd) PostMessageA(g_hwnd, WM_APP_CMD_SPEAK_END, 0, 0);
        }
    }
}

void updateWindowTitle(HWND hwnd) {
    char title[256];
    const char* stateName = g_stateNames[static_cast<int>(g_robot.state())];
    std::snprintf(title, sizeof(title),
        "Katanori Simulator [State: %s] (Keys: 1/2/3/4 | Space:Mic | Arrows:Tune Voice | ESC:Exit)",
        stateName);
    SetWindowTextA(hwnd, title);
}

LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
    case WM_CREATE:
        g_hwnd = hwnd;
        g_hal.setHwnd(hwnd);
        return 0;

    case WM_APP_CMD_SPEAK_START:
        g_robot.injectEvent(katanori::RobotEvent::RESPONSE_READY);
        g_hal.log("Event Injected (via stdin): RESPONSE_READY");
        updateWindowTitle(hwnd);
        return 0;

    case WM_APP_CMD_SPEAK_END:
        g_robot.injectEvent(katanori::RobotEvent::SPEECH_DONE);
        g_hal.log("Event Injected (via stdin): SPEECH_DONE");
        updateWindowTitle(hwnd);
        return 0;

    case WM_KEYDOWN:
        if (!(lParam & 0x40000000)) { // リピート判定除外
            switch (wParam) {
            case '1':
                std::printf("[EVENT] WAKE_WORD\n"); std::fflush(stdout);
                g_robot.injectEvent(katanori::RobotEvent::WAKE_WORD);
                g_hal.log("Event Injected: WAKE_WORD");
                break;
            case '2':
                std::printf("[EVENT] SPEECH_END\n"); std::fflush(stdout);
                g_robot.injectEvent(katanori::RobotEvent::SPEECH_END);
                g_hal.log("Event Injected: SPEECH_END");
                break;
            case '3':
                g_robot.injectEvent(katanori::RobotEvent::RESPONSE_READY);
                g_hal.log("Event Injected: RESPONSE_READY");
                break;
            case '4':
                g_robot.injectEvent(katanori::RobotEvent::SPEECH_DONE);
                g_hal.log("Event Injected: SPEECH_DONE");
                break;
            case VK_SPACE:
                g_hal.setMicPressed(true);
                break;
            case VK_UP:
                std::printf("[EVENT] FREQ_UP\n"); std::fflush(stdout);
                break;
            case VK_DOWN:
                std::printf("[EVENT] FREQ_DOWN\n"); std::fflush(stdout);
                break;
            case VK_RIGHT:
                std::printf("[EVENT] BIT_UP\n"); std::fflush(stdout);
                break;
            case VK_LEFT:
                std::printf("[EVENT] BIT_DOWN\n"); std::fflush(stdout);
                break;
            case VK_ESCAPE:
                PostQuitMessage(0);
                break;
            }
            updateWindowTitle(hwnd);
        }
        return 0;

    case WM_KEYUP:
        if (wParam == VK_SPACE) {
            g_hal.setMicPressed(false);
        }
        return 0;

    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;

    default:
        return DefWindowProcA(hwnd, msg, wParam, lParam);
    }
}

} // namespace

int main() {
    std::printf("=====================================================\n");
    std::printf(" Katanori Robot Face PC Simulator (Win32 / GDI)\n");
    std::printf("=====================================================\n");
    std::printf("Controls:\n");
    std::printf("  1     : Inject WAKE_WORD (IDLE -> LISTEN)\n");
    std::printf("  2     : Inject SPEECH_END (LISTEN -> THINK)\n");
    std::printf("  3     : Inject RESPONSE_READY (THINK -> SPEAK)\n");
    std::printf("  4     : Inject SPEECH_DONE (SPEAK -> IDLE)\n");
    std::printf("  Space : Simulate Microphone Audio Input\n");
    std::printf("  Up/Dn : Tune Voice Frequency\n");
    std::printf("  Lt/Rt : Tune Voice Bit Depth (Resolution)\n");
    std::printf("  ESC   : Exit Simulator\n");
    std::printf("=====================================================\n\n");
    std::fflush(stdout);

    // Pythonラッパーからのコマンドを受け取る監視スレッドを開始
    std::thread(StdinMonitorThread).detach();

    HINSTANCE hInstance = GetModuleHandleA(NULL);

    WNDCLASSA wc = {};
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = "KatanoriSimWindow";
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)GetStockObject(BLACK_BRUSH);

    if (!RegisterClassA(&wc)) {
        std::fprintf(stderr, "Failed to register window class.\n");
        return 1;
    }

    RECT rc = { 0, 0, WIN_W, WIN_H };
    AdjustWindowRect(&rc, WS_OVERLAPPEDWINDOW & ~WS_THICKFRAME & ~WS_MAXIMIZEBOX, FALSE);

    HWND hwnd = CreateWindowExA(
        0,
        wc.lpszClassName,
        "Katanori Simulator",
        WS_OVERLAPPEDWINDOW & ~WS_THICKFRAME & ~WS_MAXIMIZEBOX,
        CW_USEDEFAULT, CW_USEDEFAULT,
        rc.right - rc.left, rc.bottom - rc.top,
        NULL, NULL, hInstance, NULL
    );

    if (!hwnd) {
        std::fprintf(stderr, "Failed to create window.\n");
        return 1;
    }

    ShowWindow(hwnd, SW_SHOW);
    UpdateWindow(hwnd);
    updateWindowTitle(hwnd);

    MSG msg = {};
    bool running = true;
    while (running) {
        while (PeekMessageA(&msg, NULL, 0, 0, PM_REMOVE)) {
            if (msg.message == WM_QUIT) {
                running = false;
                break;
            }
            TranslateMessage(&msg);
            DispatchMessageA(&msg);
        }

        if (!running) break;

        g_robot.tick();
        Sleep(16); // ~60fps
    }

    return 0;
}