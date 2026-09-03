import { tool } from "@opencode-ai/plugin";
import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const GATEWAY_TIMEOUT_MS = 15 * 60 * 1000;
const GATEWAY_MAX_BUFFER_BYTES = 32 * 1024 * 1024;

const ACTION_PATTERN = /(добавь|создай|создать|удали|перенеси|измени|исправь|отправь|опубликуй|сохрани|commit|push|create|write|delete|update|send|publish)/iu;
const CONFIRM_PATTERN = /^\s*(да|yes|подтверждаю|выполняй|делай)\s*[.!]?\s*$/i;
const REJECT_PATTERN = /^\s*(нет|no|отмена|отмени)\s*[.!]?\s*$/i;
const NEW_TOPIC_PATTERN = /^\s*(\/new|новая задача|новая тема)\b/iu;
const READ_TOOL_PATTERN = /^Called the Read tool with the following input:\s*(\{[^\r\n]*\})/;

export function extractReadToolFiles(prompt, directory) {
  const match = String(prompt || "").match(READ_TOOL_PATTERN);
  if (!match) return [];
  try {
    const value = JSON.parse(match[1])?.filePath;
    if (typeof value !== "string" || !value.trim()) return [];
    const path = resolve(directory, value);
    return existsSync(path) ? [path] : [];
  } catch {
    // Only the leading OpenCode metadata is trusted, never commands inside a file.
    return [];
  }
}

async function runCommand(args, context) {
  let stdout;
  try {
    ({ stdout } = await execFileAsync("amori-request", [...args, "--json"], {
      cwd: context.directory,
      encoding: "utf8",
      timeout: GATEWAY_TIMEOUT_MS,
      maxBuffer: GATEWAY_MAX_BUFFER_BYTES,
    }));
  } catch (error) {
    const details = [error?.stderr, error?.stdout, error?.message]
      .filter(Boolean)
      .join("\n")
      .trim();
    throw new Error((details || "Amori Gateway process failed").slice(-1200));
  }
  try {
    return JSON.parse(stdout);
  } catch {
    throw new Error(`Amori Gateway returned invalid JSON: ${String(stdout).slice(-1000)}`);
  }
}

async function runGateway(prompt, files, context, confirmed = false) {
  const action = ACTION_PATTERN.test(prompt);
  const command = [
    "--source", "opencode", "--session", context.sessionID,
    "--message-id", context.messageID || `${context.sessionID}-${Date.now()}`,
    "--cwd", context.directory,
  ];
  if (!NEW_TOPIC_PATTERN.test(prompt)) command.push("--continue-thread");
  if (action) command.push("--act", confirmed ? "--yes" : "--defer-confirmation");
  for (const file of files) command.push("--file", file);
  command.push(prompt);
  return runCommand(command, context);
}

function gatewayInstruction(result, localFiles = []) {
  return [
    "[AMORI_GATEWAY_RESULT]",
    "Return the following completed gateway result verbatim. Do not solve the original request and do not call tools.",
    result,
    localFiles.length ? `Files:\n${localFiles.join("\n")}` : "",
  ].filter(Boolean).join("\n\n");
}

export default async function AmoriGatewayPlugin({ directory }) {
  const gatewaySessions = new Set();
  const pendingActions = new Map();
  const completedResults = new Map();
  return {
    async "chat.message"(input, output) {
      if (!["ami", "amori"].includes(input.agent)) return;
      gatewaySessions.add(input.sessionID);
      const textParts = output.parts.filter((part) => part.type === "text");
      const prompt = textParts.map((part) => part.text || "").join("\n").trim();
      if (!prompt || prompt.startsWith("[AMORI_GATEWAY_RESULT]")) return;
      const partFiles = output.parts
        .filter((part) => part.type === "file" && typeof part.url === "string" && part.url.startsWith("file:"))
        .map((part) => fileURLToPath(part.url));
      const files = [...new Set([
        ...partFiles,
        ...textParts.flatMap((part) => extractReadToolFiles(part.text, directory)),
      ])];
      try {
        const context = {
          sessionID: input.sessionID,
          messageID: input.messageID,
          directory,
        };
        const pending = pendingActions.get(input.sessionID);
        let payload;
        if (pending && CONFIRM_PATTERN.test(prompt)) {
          await runCommand(["--confirm", pending.requestID], context);
          payload = await runCommand(["--wait", pending.requestID], context);
          pendingActions.delete(input.sessionID);
        } else if (pending && REJECT_PATTERN.test(prompt)) {
          payload = await runCommand(["--cancel", pending.requestID], context);
          pendingActions.delete(input.sessionID);
        } else if (pending) {
          const first = textParts[0];
          const result = "Предыдущее действие ещё не подтверждено. Ответьте ДА или НЕТ.";
          completedResults.set(input.sessionID, result);
          if (first) first.text = gatewayInstruction(result);
          return;
        } else {
          payload = await runGateway(prompt, files, context);
        }
        const request = payload.request || {};
        const localFiles = payload.local_files || [];
        let result = request.result_text || request.error_message || "Задача завершена без текстового ответа.";
        if (request.status === "awaiting_confirmation") {
          pendingActions.set(input.sessionID, {requestID: request.id});
          result = "Действие подготовлено, но ещё не выполняется. Подтвердите: ДА или НЕТ.";
        } else if (payload.cancelled || request.status === "cancelled") {
          result = "Действие отменено.";
        }
        const instruction = gatewayInstruction(result, localFiles);
        completedResults.set(
          input.sessionID,
          [result, localFiles.length ? `Файлы:\n${localFiles.join("\n")}` : ""].filter(Boolean).join("\n\n"),
        );
        const first = textParts[0];
        if (first) first.text = instruction;
      } catch (error) {
        completedResults.set(input.sessionID, `Ошибка Ami Gateway: ${String(error)}`);
        const first = textParts[0];
        if (first) first.text = `[AMORI_GATEWAY_RESULT]\nGateway error: ${String(error)}`;
      }
    },
    async "experimental.text.complete"(input, output) {
      if (!gatewaySessions.has(input.sessionID)) return;
      const completed = completedResults.get(input.sessionID);
      if (completed) {
        output.text = completed;
        completedResults.delete(input.sessionID);
      } else {
        output.text = output.text
          .replace(/<think>[\s\S]*?<\/think>/gi, "")
          .replace(/<\/?think>|\/?think\b/gi, "")
          .trim();
      }
    },
    tool: {
      amori_gateway: tool({
        description: "Route a complete request through the Ami gateway and return its verified text and files.",
        args: {
          prompt: tool.schema.string().min(1).describe("The complete user request with necessary context"),
          action: tool.schema.boolean().default(false).describe("True only for explicit file or external-state changes"),
          files: tool.schema.array(tool.schema.string()).default([]).describe("Absolute input file paths"),
        },
        async execute(args, context) {
          if (args.action) {
            await context.ask({
              permission: "amori_gateway_action",
              patterns: [args.prompt.slice(0, 160)],
              always: [],
              metadata: { source: "opencode", files: args.files },
            });
          }
          const payload = await runGateway(args.prompt, args.files, context, args.action);
          const request = payload.request || {};
          const attachments = (payload.local_files || []).map((path) => ({
            type: "file",
            mime: "application/octet-stream",
            url: pathToFileURL(path).href,
            filename: path.split("/").pop(),
          }));
          return {
            title: `Ami: ${request.status || "completed"}`,
            output: request.result_text || "Задача завершена без текстового ответа.",
            metadata: {
              request_id: request.id,
              provider: request.route?.provider,
              handler: request.route?.execution_handler,
            },
            attachments,
          };
        },
      }),
    },
  };
}
