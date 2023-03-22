import WebSocket from 'ws';
import * as diff from 'diff';
import { readFileSync } from "fs";
const getSocketUrl = async (wx_id) => {
    const socketUrl = 'wss://tch252531.tch.quora.com';
    const credentials = JSON.parse(readFileSync("config.json", "utf8"));
    const appSettings = credentials[wx_id].app_settings.tchannelData;
    const boxName = appSettings.boxName;
    const minSeq = appSettings.minSeq;
    const channel = appSettings.channel;
    const hash = appSettings.channelHash;
    return `${socketUrl}/up/${boxName}/updates?min_seq=${minSeq}&channel=${channel}&hash=${hash}`;
};
export const connectWs = async (wx_id) => {
    const url = await getSocketUrl(wx_id);
    const ws = new WebSocket(url);
    return new Promise((resolve, reject) => {
        ws.on('open', function open() {
            console.log("Connected to websocket");
            return resolve(ws);
        });
    });
};
export const disconnectWs = async (ws) => {
    return new Promise((resolve, reject) => {
        ws.on('close', function close() {
            return resolve(true);
        });
        ws.close();
    });
};
export const listenWs = async (ws) => {
    let previousText = '';
    return new Promise((resolve, reject) => {
        const onMessage = function incoming(data) {
            let jsonData = JSON.parse(data);
            if (jsonData.messages && jsonData.messages.length > 0) {
                const messages = JSON.parse(jsonData.messages[0]);
                const dataPayload = messages.payload.data;
                const text = dataPayload.messageAdded.text;
                const state = dataPayload.messageAdded.state;
                if (state !== 'complete') {
                    const differences = diff.diffChars(previousText, text);
                    let result = '';
                    differences.forEach((part) => {
                        if (part.added) {
                            result += part.value;
                        }
                    });
                    previousText = text;
                    process.stdout.write(result);
                }
                else {
                    ws.removeListener('message', onMessage);
                    process.stdout.write("\n");
                    return resolve(previousText);
                }
            }
        };
        ws.on('message', onMessage);
    });
};
