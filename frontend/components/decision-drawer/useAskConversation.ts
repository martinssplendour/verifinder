"use client";

import { useRef, useState } from "react";
import { ApiError, askVeriFinder } from "@/services/api";
import type { AskResponse } from "@/types";

/** Entitlement refusals get their own panel, so they are not shown as errors too. */
export function isBlocking(error: ApiError): boolean {
  return error.paymentRequired || error.upgradeRequired || error.signInRequired;
}

export type ChatMessage = { id: number; role: "assistant" | "user"; text: string; ask?: AskResponse };

const INITIAL_ASK: ChatMessage[] = [{ id: 1, role: "assistant", text: "What would you like me to check? I can query sponsorship, qualifications, study providers, food hygiene, recent property sales and exact-postcode area evidence." }];

type Options = {
  setLoading: (value: boolean) => void;
  setError: (value: string | null) => void;
  setBlocked: (value: ApiError | null) => void;
};

export function useAskConversation({ setLoading, setError, setBlocked }: Options) {
  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_ASK);
  const nextId = useRef(10);

  function message(role: "assistant" | "user", text: string, ask?: AskResponse): ChatMessage {
    return { id: nextId.current++, role, text, ask };
  }

  async function submit(question: string) {
    setError(null);
    setBlocked(null);
    setMessages((current) => [...current, message("user", question)]);
    setLoading(true);
    try {
      const answer = await askVeriFinder(question);
      setMessages((current) => [...current, message("assistant", answer.summary, answer)]);
    } catch (requestError) {
      setError(requestError instanceof ApiError && isBlocking(requestError) ? null : (requestError as Error).message);
      setBlocked(requestError instanceof ApiError && isBlocking(requestError) ? requestError : null);
    } finally {
      setLoading(false);
    }
  }

  return { messages, submit };
}
