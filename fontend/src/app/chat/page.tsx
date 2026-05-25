"use client";

import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { chatService } from "@/services/data-service";
import { Send, User, Bot, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const mutation = useMutation({
    mutationFn: (q: string) => chatService.send(q),
    onSuccess: (data) => {
      setMessages((prev) => [...prev, { role: "assistant", content: data.response }]);
    },
    onError: (err) => {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Lỗi: Không thể kết nối với trí tuệ nhân tạo." },
      ]);
    },
  });

  const handleSend = () => {
    if (!input.trim() || mutation.isPending) return;
    const q = input.trim();
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setInput("");
    mutation.mutate(q);
  };

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, mutation.isPending]);

  return (
    <div className="flex flex-col h-screen max-h-screen">
      <header className="p-4 border-b border-zinc-200 bg-white">
        <h2 className="font-bold">AI Analyst</h2>
        <p className="text-xs text-zinc-500">Hỏi về dữ liệu kinh tế ASEAN</p>
      </header>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-zinc-400 gap-2">
            <Bot className="h-12 w-12 opacity-20" />
            <p>Bắt đầu cuộc hội thoại bằng một câu hỏi</p>
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={cn(
              "flex gap-3 max-w-[85%]",
              m.role === "user" ? "ml-auto flex-row-reverse" : "mr-auto"
            )}
          >
            <div className={cn(
              "h-8 w-8 rounded-full flex items-center justify-center shrink-0",
              m.role === "user" ? "bg-zinc-900 text-white" : "bg-zinc-200 text-zinc-600"
            )}>
              {m.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            </div>
            <div className={cn(
              "p-3 rounded-2xl text-sm leading-relaxed prose prose-sm dark:prose-invert",
              m.role === "user" ? "bg-zinc-900 text-white" : "bg-white border border-zinc-200"
            )}>
              <ReactMarkdown>
                {m.content}
              </ReactMarkdown>
            </div>
          </div>
        ))}

        {mutation.isPending && (
          <div className="flex gap-3 mr-auto">
            <div className="h-8 w-8 rounded-full bg-zinc-200 text-zinc-600 flex items-center justify-center shrink-0">
              <Bot className="h-4 w-4" />
            </div>
            <div className="p-4 rounded-2xl bg-white border border-zinc-200 flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-zinc-400" />
              <span className="text-sm text-zinc-500">Đang suy nghĩ...</span>
            </div>
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      <div className="p-4 bg-white border-t border-zinc-200">
        <div className="max-w-4xl mx-auto flex gap-2">
          <input
            className="flex-1 bg-zinc-100 border-none rounded-full px-4 py-2 text-sm focus:ring-2 focus:ring-zinc-900 outline-none"
            placeholder="Ví dụ: So sánh GDP Việt Nam và Thái Lan 2023..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
          />
          <button
            onClick={handleSend}
            disabled={mutation.isPending}
            className="h-9 w-9 bg-zinc-900 text-white rounded-full flex items-center justify-center disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
