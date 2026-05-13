import { useEffect, useRef, useState } from "react";
import { io } from "socket.io-client";

export default function useWebSocket() {
  const [lastMessage, setLastMessage] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef(null);

  useEffect(() => {
    const socket = io("http://localhost:5000", {
      transports: ["websocket", "polling"],
    });
    socketRef.current = socket;

    socket.on("connect", () => {
      console.log("[WS] 已连接, transport:", socket.io.engine.transport.name);
      setIsConnected(true);
    });

    socket.on("classification", (p) => {
      setLastMessage(p);
    });

    socket.on("statistics", (p) => {
      setLastMessage(p);
    });

    socket.on("disconnect", (reason) => {
      console.log("[WS] 断开:", reason);
      setIsConnected(false);
    });

    socket.on("connect_error", (err) => {
      console.log("[WS] 连接错误:", err.message);
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  return { lastMessage, isConnected };
}
