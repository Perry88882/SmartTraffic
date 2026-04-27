import { useEffect, useRef, useState, useCallback } from "react";
import { io } from "socket.io-client";

const WS_URL = "http://localhost:5000";

/**
 * 自定义 Hook：封装 SocketIO 连接与自动重连逻辑。
 *
 * @param {string} namespace - SocketIO 命名空间（默认 "/"）
 * @returns {{ lastMessage: object|null, sendMessage: (event: string, data: any) => void, isConnected: boolean }}
 */
export default function useWebSocket(namespace = "/") {
  const socketRef = useRef(null);
  const [lastMessage, setLastMessage] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const socket = io(WS_URL + namespace, {
      transports: ["websocket", "polling"],
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    });
    socketRef.current = socket;

    socket.on("connect", () => {
      console.log("[useWebSocket] 已连接:", socket.id);
      setIsConnected(true);
    });

    // 监听后端推送的分类事件
    socket.on("classification", (payload) => {
      setLastMessage(payload);
    });

    // 监听后端推送的统计事件
    socket.on("statistics", (payload) => {
      setLastMessage(payload);
    });

    socket.on("disconnect", (reason) => {
      console.log("[useWebSocket] 断开连接:", reason);
      setIsConnected(false);
    });

    socket.on("connect_error", (err) => {
      console.warn("[useWebSocket] 连接错误:", err.message);
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [namespace]);

  const sendMessage = useCallback((event, data) => {
    if (socketRef.current && socketRef.current.connected) {
      socketRef.current.emit(event, data);
    }
  }, []);

  return { lastMessage, sendMessage, isConnected };
}
