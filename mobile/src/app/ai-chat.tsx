import React, { useState, useRef } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Bot, Send } from "lucide-react-native";
import { api } from "@/lib/api";
import { colors, spacing, fonts, radius } from "@/lib/theme";

const HEADER_ICON = 32;
const ACCENT = "#5CAE5D";

interface Message {
  id: string;
  type: "user" | "ai";
  text: string;
  originalQuestion?: string;
}

export default function AIChatScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const flatListRef = useRef<FlatList<Message>>(null);

  async function sendQuestion(question: string, detailed = false) {
    if (!question.trim() && !detailed) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      type: "user",
      text: question.trim(),
    };

    if (!detailed) {
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
    }

    setLoading(true);
    try {
      const res = await api.askAI(question.trim(), detailed);
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        type: "ai",
        text: res.answer,
        originalQuestion: question.trim(),
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch {
      const errMsg: Message = {
        id: (Date.now() + 1).toString(),
        type: "ai",
        text: "Не удалось получить ответ. Попробуйте ещё раз.",
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
      setTimeout(
        () => flatListRef.current?.scrollToEnd({ animated: true }),
        100,
      );
    }
  }

  function renderMessage({ item }: { item: Message }) {
    const isUser = item.type === "user";
    return (
      <View
        style={[
          styles.messageBubble,
          isUser ? styles.userBubble : styles.aiBubble,
        ]}
      >
        {!isUser && <Text style={styles.aiLabel}>🤖 AI</Text>}
        <Text
          style={[styles.messageText, isUser && styles.userText]}
          selectable
        >
          {item.text}
        </Text>
        {!isUser && item.originalQuestion && (
          <TouchableOpacity
            style={styles.detailBtn}
            onPress={() => sendQuestion(item.originalQuestion!, true)}
            disabled={loading}
          >
            <Text style={styles.detailBtnText}>Подробнее →</Text>
          </TouchableOpacity>
        )}
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <View style={styles.header}>
        <Bot size={HEADER_ICON} color={ACCENT} strokeWidth={2} />
        <Text style={styles.headerTitle}>AI-ассистент</Text>
      </View>
      <KeyboardAvoidingView
        style={styles.screen}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={Platform.OS === "ios" ? 90 : 0}
      >
        {messages.length === 0 ? (
          <View style={styles.placeholder}>
            <Text style={styles.placeholderEmoji}>🤖</Text>
            <Text style={styles.placeholderText}>
              Задайте вопрос AI-ассистенту
            </Text>
            <Text style={styles.placeholderSub}>
              Спросите о франшизе, управлении салоном или финансах
            </Text>
          </View>
        ) : (
          <FlatList
            ref={flatListRef}
            data={messages}
            renderItem={renderMessage}
            keyExtractor={(item) => item.id}
            contentContainerStyle={styles.messagesList}
            onContentSizeChange={() =>
              flatListRef.current?.scrollToEnd({ animated: true })
            }
          />
        )}

        {loading && (
          <View style={styles.loadingRow}>
            <ActivityIndicator size="small" color={colors.accent} />
            <Text style={styles.loadingText}>AI думает...</Text>
          </View>
        )}

        <View style={styles.inputRow}>
          <TextInput
            style={styles.input}
            placeholder="Введите вопрос..."
            placeholderTextColor={colors.textMuted}
            value={input}
            onChangeText={setInput}
            onSubmitEditing={() => sendQuestion(input)}
            returnKeyType="send"
            editable={!loading}
            multiline
          />
          <TouchableOpacity
            style={[
              styles.sendBtn,
              (!input.trim() || loading) && styles.sendBtnDisabled,
            ]}
            disabled={!input.trim() || loading}
            onPress={() => sendQuestion(input)}
          >
            <Send size={22} color={colors.white} strokeWidth={2} />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
    paddingBottom: spacing.md,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: "600",
    color: colors.text,
  },
  screen: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  placeholder: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    padding: spacing.xl,
  },
  placeholderEmoji: {
    fontSize: 56,
  },
  placeholderText: {
    ...fonts.large,
    textAlign: "center",
  },
  placeholderSub: {
    ...fonts.caption,
    textAlign: "center",
    lineHeight: 18,
  },
  messagesList: {
    padding: spacing.md,
    gap: spacing.sm,
    paddingBottom: spacing.md,
  },
  messageBubble: {
    borderRadius: radius.md,
    padding: spacing.md,
    maxWidth: "85%",
  },
  userBubble: {
    backgroundColor: ACCENT,
    alignSelf: "flex-end",
  },
  aiBubble: {
    backgroundColor: colors.white,
    alignSelf: "flex-start",
    borderWidth: 1,
    borderColor: "#E5E5EA",
  },
  aiLabel: {
    ...fonts.caption,
    color: colors.textSecondary,
    fontWeight: "600",
    marginBottom: spacing.xs,
  },
  messageText: {
    ...fonts.regular,
    lineHeight: 22,
    color: colors.text,
  },
  userText: {
    color: colors.white,
    fontWeight: "600",
  },
  detailBtn: {
    marginTop: spacing.sm,
    alignSelf: "flex-start",
  },
  detailBtnText: {
    ...fonts.caption,
    color: ACCENT,
    fontWeight: "600",
  },
  loadingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
  },
  loadingText: {
    ...fonts.caption,
    color: colors.textMuted,
  },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
    paddingBottom: 120,
    gap: spacing.sm,
    backgroundColor: colors.bg,
  },
  input: {
    flex: 1,
    backgroundColor: colors.white,
    borderRadius: 22,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    color: colors.text,
    fontSize: 16,
    minHeight: 44,
    maxHeight: 100,
    borderWidth: 0,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  sendBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: ACCENT,
    alignItems: "center",
    justifyContent: "center",
  },
  sendBtnDisabled: {
    opacity: 0.4,
  },
});
