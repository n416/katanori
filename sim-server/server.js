import { WebSocketServer } from 'ws';
import * as dotenv from 'dotenv';
import { GoogleGenAI } from '@google/genai';

dotenv.config();

const port = process.env.PORT || 8080;
const wss = new WebSocketServer({ port });

// Initialize Gemini API
const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY || 'dummy_key' });

console.log(`WebSocket Server (DO Mock) started on ws://localhost:${port}`);

wss.on('connection', (ws) => {
  console.log('Robot connected.');

  // Welcome message
  ws.send(JSON.stringify({ type: 'sys', message: 'Connected to DO Mock Server.' }));

  ws.on('message', async (message) => {
    try {
      const data = JSON.parse(message);
      console.log('Received from Robot:', data);

      if (data.type === 'text') {
        const userText = data.text;
        
        // モック応答（APIキーがない場合）
        if (!process.env.GEMINI_API_KEY || process.env.GEMINI_API_KEY === 'dummy_key') {
           setTimeout(() => {
             ws.send(JSON.stringify({ type: 'text', text: `(Mock) 「${userText}」ですね。APIキーが未設定です。` }));
           }, 1500); // 1.5秒のラグを意図的に作成
           return;
        }

        // Call Gemini API
        try {
          const response = await ai.models.generateContent({
            model: 'gemini-2.5-pro',
            contents: `あなたは「カタノリロボ」という小さな肩乗りロボットです。フレンドリーに短く（1文程度で）返答してください。\nユーザー: ${userText}`
          });
          
          ws.send(JSON.stringify({ type: 'text', text: response.text }));
        } catch (apiError) {
          console.error('Gemini API Error:', apiError);
          ws.send(JSON.stringify({ type: 'error', text: 'Gemini APIエラーが発生しました。' }));
        }
      }
    } catch (e) {
      console.error('Message format error:', e);
    }
  });

  ws.on('close', () => {
    console.log('Robot disconnected.');
  });
});
