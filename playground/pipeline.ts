// ABOUTME: TypeScript port of the Python pipeline. Mirrors prompts + chunking exactly.
// ABOUTME: Returns WAV bytes (no ffmpeg in the browser — Gemini already emits PCM we just wrap).

import { GoogleGenAI } from "@google/genai";

export type Section = { title: string; content: string };

export type PodcastConfig = {
	hostAName: string;
	hostBName: string;
	hostAVoice: string;
	hostBVoice: string;
	personaHint?: string;
	targetWordsMin?: number;
	targetWordsMax?: number;
};

export type Turn = { speaker: string; text: string };

export type ProgressEvent =
	| { phase: "script_gen"; message: string }
	| { phase: "synthesize"; chunk: number; totalChunks: number }
	| { phase: "encode"; message: string }
	| { phase: "done"; turns: number; bytes: number; durations: Record<string, number> };

export type GeneratePodcastArgs = {
	apiKey: string;
	subject: string;
	sections: Section[];
	config: PodcastConfig;
	onProgress?: (e: ProgressEvent) => void;
	scriptModel?: string;
	ttsModel?: string;
};

const DEFAULT_SCRIPT_MODEL = "gemini-2.5-pro";
const DEFAULT_TTS_MODEL = "gemini-2.5-flash-preview-tts";
const CHUNK_WORD_BUDGET = 450;
const PCM_SAMPLE_RATE = 24_000;
const PCM_SAMPLE_WIDTH = 2;
const PCM_CHANNELS = 1;

function buildPrompt(subject: string, sections: Section[], config: PodcastConfig): string {
	const sectionBlocks = sections.map((s) => `### ${s.title}\n${s.content}`).join("\n\n");
	const scopeLabel =
		sections.length > 3
			? "the full source material"
			: `these sections: ${sections.map((s) => s.title).join(", ")}`;
	const personaLine = config.personaHint ? `PERSONA: ${config.personaHint}\n\n` : "";
	const wordsMin = config.targetWordsMin ?? 1100;
	const wordsMax = config.targetWordsMax ?? 1500;

	return `You are writing a two-host podcast script about: ${subject}.

${personaLine}HOSTS (use these exact names as speaker labels):
- ${config.hostAName} — leads the conversation; introduces topics; asks the sharpest follow-up.
- ${config.hostBName} — analytical counterpart; brings specific numbers, dates, names; pushes back when claims feel thin.

SCOPE: Cover ${scopeLabel}. Do not invent facts not present in the source. If the source omits something, omit it from the script.

LENGTH: ${wordsMin}-${wordsMax} words of dialogue (excluding labels). Pace naturally; do not pad.

STYLE RULES:
- Open with a 1-2 sentence cold intro from ${config.hostAName}, no greeting or "welcome back".
- Hosts cite specifics by name (people, numbers, dates) — never vague references like "the founder" or "the company".
- Skip filler like "great point", "absolutely", "what's fascinating".
- End with a one-line beat that gives the listener a take to chew on. No sign-off, no outro music cue.
- No music, sound effects, or stage directions. Plain dialogue only.

OUTPUT FORMAT — strict JSON array of turn objects, no markdown, no commentary:
[
  {"speaker": "${config.hostAName}", "text": "..."},
  {"speaker": "${config.hostBName}", "text": "..."},
  ...
]

SOURCE MATERIAL:

${sectionBlocks}
`;
}

function parseDialogue(raw: string, hostA: string, hostB: string): Turn[] {
	const cleaned = raw.replace(/^```(?:json)?\s*|\s*```$/gm, "").trim();
	const data = JSON.parse(cleaned);
	if (!Array.isArray(data)) throw new Error(`Expected JSON array, got ${typeof data}`);
	const allowed = new Set([hostA, hostB]);
	const turns: Turn[] = [];
	data.forEach((item: unknown, i: number) => {
		if (!item || typeof item !== "object") throw new Error(`Turn ${i} is not an object`);
		const it = item as { speaker?: unknown; text?: unknown };
		const speaker = String(it.speaker ?? "").trim();
		const text = String(it.text ?? "").trim();
		if (!allowed.has(speaker)) {
			throw new Error(`Turn ${i} speaker "${speaker}" not in [${hostA}, ${hostB}]`);
		}
		if (text) turns.push({ speaker, text });
	});
	if (turns.length < 4) throw new Error(`Dialogue too short (${turns.length} turns)`);
	const used = new Set(turns.map((t) => t.speaker));
	if (used.size !== 2) throw new Error(`Dialogue uses only ${[...used]}, expected both hosts`);
	return turns;
}

function chunkTurns(turns: Turn[]): Turn[][] {
	const chunks: Turn[][] = [];
	let current: Turn[] = [];
	let currentWords = 0;
	for (const turn of turns) {
		const words = turn.text.split(/\s+/).filter(Boolean).length;
		if (current.length > 0 && currentWords + words > CHUNK_WORD_BUDGET) {
			chunks.push(current);
			current = [];
			currentWords = 0;
		}
		current.push(turn);
		currentWords += words;
	}
	if (current.length > 0) chunks.push(current);
	return chunks;
}

function formatChunkText(turns: Turn[]): string {
	return turns.map((t) => `${t.speaker}: ${t.text}`).join("\n");
}

// Convert base64 (Gemini returns inline audio data as base64) to Uint8Array of raw PCM.
function base64ToUint8(b64: string): Uint8Array {
	const bin = atob(b64);
	const bytes = new Uint8Array(bin.length);
	for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
	return bytes;
}

// Wrap concatenated PCM (24kHz signed 16-bit mono) in a WAV header so browsers can play it.
function wrapPcmAsWav(pcm: Uint8Array): Uint8Array {
	const dataLen = pcm.byteLength;
	const buffer = new ArrayBuffer(44 + dataLen);
	const view = new DataView(buffer);
	const writeStr = (off: number, s: string) => {
		for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i));
	};
	writeStr(0, "RIFF");
	view.setUint32(4, 36 + dataLen, true);
	writeStr(8, "WAVE");
	writeStr(12, "fmt ");
	view.setUint32(16, 16, true); // PCM fmt chunk size
	view.setUint16(20, 1, true); // PCM format
	view.setUint16(22, PCM_CHANNELS, true);
	view.setUint32(24, PCM_SAMPLE_RATE, true);
	view.setUint32(28, PCM_SAMPLE_RATE * PCM_CHANNELS * PCM_SAMPLE_WIDTH, true); // byte rate
	view.setUint16(32, PCM_CHANNELS * PCM_SAMPLE_WIDTH, true); // block align
	view.setUint16(34, PCM_SAMPLE_WIDTH * 8, true); // bits per sample
	writeStr(36, "data");
	view.setUint32(40, dataLen, true);
	new Uint8Array(buffer, 44).set(pcm);
	return new Uint8Array(buffer);
}

async function synthesizeChunk(
	client: GoogleGenAI,
	turns: Turn[],
	config: PodcastConfig,
	ttsModel: string,
): Promise<Uint8Array> {
	const response = await client.models.generateContent({
		model: ttsModel,
		contents: formatChunkText(turns),
		config: {
			responseModalities: ["AUDIO"],
			speechConfig: {
				multiSpeakerVoiceConfig: {
					speakerVoiceConfigs: [
						{
							speaker: config.hostAName,
							voiceConfig: { prebuiltVoiceConfig: { voiceName: config.hostAVoice } },
						},
						{
							speaker: config.hostBName,
							voiceConfig: { prebuiltVoiceConfig: { voiceName: config.hostBVoice } },
						},
					],
				},
			},
		},
	});

	const candidates = response.candidates ?? [];
	if (candidates.length === 0) {
		const feedback = (response as { promptFeedback?: unknown }).promptFeedback;
		throw new Error(
			`Gemini TTS returned no candidates (${turns.length} turns) — possible safety block or quota; feedback=${JSON.stringify(feedback)}`,
		);
	}
	const parts = candidates[0]?.content?.parts ?? [];
	for (const part of parts) {
		const data = (part as { inlineData?: { data?: string } }).inlineData?.data;
		if (data) return base64ToUint8(data);
	}
	throw new Error("Gemini TTS returned no inline audio data");
}

export async function generatePodcast(args: GeneratePodcastArgs): Promise<{
	wavBytes: Uint8Array;
	turns: Turn[];
	durationsMs: Record<string, number>;
}> {
	const { apiKey, subject, sections, config, onProgress } = args;
	if (config.hostAName === config.hostBName) throw new Error("host names must differ");
	if (config.hostAVoice === config.hostBVoice) throw new Error("host voices must differ");
	if (sections.length === 0) throw new Error("At least one Section is required");

	const client = new GoogleGenAI({ apiKey });
	const scriptModel = args.scriptModel ?? DEFAULT_SCRIPT_MODEL;
	const ttsModel = args.ttsModel ?? DEFAULT_TTS_MODEL;
	const durations: Record<string, number> = {};

	// --- 1. Script generation ---
	onProgress?.({ phase: "script_gen", message: `Generating dialogue with ${scriptModel}…` });
	const t0 = performance.now();
	const scriptResp = await client.models.generateContent({
		model: scriptModel,
		contents: buildPrompt(subject, sections, config),
		config: { temperature: 0.4, responseMimeType: "application/json" },
	});
	const raw = scriptResp.text ?? "";
	if (!raw) throw new Error("Empty response from script-gen LLM");
	const turns = parseDialogue(raw, config.hostAName, config.hostBName);
	durations.scriptGen = Math.round(performance.now() - t0);

	// --- 2. Synthesis (chunked) ---
	const chunks = chunkTurns(turns);
	const t1 = performance.now();
	const pcmParts: Uint8Array[] = [];
	for (let i = 0; i < chunks.length; i++) {
		onProgress?.({ phase: "synthesize", chunk: i + 1, totalChunks: chunks.length });
		pcmParts.push(await synthesizeChunk(client, chunks[i]!, config, ttsModel));
	}
	durations.synthesize = Math.round(performance.now() - t1);

	// --- 3. WAV wrap (no ffmpeg) ---
	const t2 = performance.now();
	onProgress?.({ phase: "encode", message: "Wrapping PCM as WAV…" });
	const totalLen = pcmParts.reduce((sum, p) => sum + p.byteLength, 0);
	const combined = new Uint8Array(totalLen);
	let offset = 0;
	for (const p of pcmParts) {
		combined.set(p, offset);
		offset += p.byteLength;
	}
	const wavBytes = wrapPcmAsWav(combined);
	durations.encode = Math.round(performance.now() - t2);

	onProgress?.({
		phase: "done",
		turns: turns.length,
		bytes: wavBytes.byteLength,
		durations,
	});
	return { wavBytes, turns, durationsMs: durations };
}
