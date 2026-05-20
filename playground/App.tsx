// ABOUTME: Browser playground for gemini-podcast. BYO API key (stays in localStorage,
// ABOUTME: never sent anywhere except api.google.com). Paste content → get an audio file.

import { useEffect, useMemo, useRef, useState } from "react";
import { generatePodcast, type Section, type Turn } from "./pipeline";
import { VOICE_PAIRS } from "./voices";

type Status =
	| { kind: "idle" }
	| { kind: "running"; phase: string; detail: string }
	| { kind: "done"; url: string; turns: Turn[]; durations: Record<string, number>; bytes: number }
	| { kind: "error"; message: string };

const SAMPLE_SUBJECT = "why the QWERTY keyboard layout won";
const SAMPLE_SECTIONS: Section[] = [
	{
		title: "Origin",
		content:
			"QWERTY was designed in the 1870s by Christopher Sholes for the Sholes & Glidden typewriter — the first commercially successful typewriter. The layout was tuned to space frequently-paired letters apart so the mechanical typebars wouldn't jam — not, as the common myth goes, to slow typists down.",
	},
	{
		title: "Lock-in",
		content:
			"By 1888 a touch-typing champion named Frank McGurrin demonstrated QWERTY's superiority over rival layouts in a widely-publicized speed contest. Schools standardized on it, manufacturers followed, and switching costs compounded. Dvorak's 1936 redesign showed measurable speed gains in lab studies but never broke the network effect.",
	},
];

const LS_KEY = "gemini-podcast-playground:apiKey";

export function App() {
	const [apiKey, setApiKey] = useState<string>(() => localStorage.getItem(LS_KEY) ?? "");
	const [rememberKey, setRememberKey] = useState(true);

	const [subject, setSubject] = useState(SAMPLE_SUBJECT);
	const [sections, setSections] = useState<Section[]>(SAMPLE_SECTIONS);

	const [hostAName, setHostAName] = useState("Alex");
	const [hostBName, setHostBName] = useState("Maya");
	const [pairIdx, setPairIdx] = useState(0);
	const [personaHint, setPersonaHint] = useState(
		"two thoughtful explainers, dry not breathless",
	);

	const [status, setStatus] = useState<Status>({ kind: "idle" });
	const lastUrlRef = useRef<string | null>(null);

	useEffect(() => {
		return () => {
			if (lastUrlRef.current) URL.revokeObjectURL(lastUrlRef.current);
		};
	}, []);

	useEffect(() => {
		if (rememberKey && apiKey) localStorage.setItem(LS_KEY, apiKey);
		if (!rememberKey) localStorage.removeItem(LS_KEY);
	}, [apiKey, rememberKey]);

	const pair = VOICE_PAIRS[pairIdx]!;

	function updateSection(i: number, patch: Partial<Section>) {
		setSections((prev) => prev.map((s, idx) => (idx === i ? { ...s, ...patch } : s)));
	}
	function addSection() {
		setSections((prev) => [...prev, { title: "", content: "" }]);
	}
	function removeSection(i: number) {
		setSections((prev) => prev.filter((_, idx) => idx !== i));
	}

	async function onGenerate() {
		if (!apiKey.trim()) {
			setStatus({ kind: "error", message: "Paste your Gemini API key first." });
			return;
		}
		if (!subject.trim()) {
			setStatus({ kind: "error", message: "Subject is required." });
			return;
		}
		const filledSections = sections.filter((s) => s.title.trim() && s.content.trim());
		if (filledSections.length === 0) {
			setStatus({ kind: "error", message: "Add at least one section with title + content." });
			return;
		}

		if (lastUrlRef.current) {
			URL.revokeObjectURL(lastUrlRef.current);
			lastUrlRef.current = null;
		}

		setStatus({ kind: "running", phase: "script_gen", detail: "Starting…" });
		try {
			const { wavBytes, turns, durationsMs } = await generatePodcast({
				apiKey: apiKey.trim(),
				subject: subject.trim(),
				sections: filledSections,
				config: {
					hostAName: hostAName.trim() || "Alex",
					hostBName: hostBName.trim() || "Maya",
					hostAVoice: pair.voiceA,
					hostBVoice: pair.voiceB,
					personaHint: personaHint.trim(),
				},
				onProgress: (e) => {
					if (e.phase === "script_gen") {
						setStatus({ kind: "running", phase: "script_gen", detail: e.message });
					} else if (e.phase === "synthesize") {
						setStatus({
							kind: "running",
							phase: "synthesize",
							detail: `Synthesizing chunk ${e.chunk}/${e.totalChunks}…`,
						});
					} else if (e.phase === "encode") {
						setStatus({ kind: "running", phase: "encode", detail: e.message });
					}
				},
			});
			const blob = new Blob([wavBytes.buffer as ArrayBuffer], { type: "audio/wav" });
			const url = URL.createObjectURL(blob);
			lastUrlRef.current = url;
			setStatus({
				kind: "done",
				url,
				turns,
				durations: durationsMs,
				bytes: wavBytes.byteLength,
			});
		} catch (err) {
			setStatus({
				kind: "error",
				message: err instanceof Error ? err.message : String(err),
			});
		}
	}

	const isRunning = status.kind === "running";

	return (
		<div style={styles.page}>
			<header style={styles.header}>
				<h1 style={styles.title}>gemini-podcast playground</h1>
				<p style={styles.subtitle}>
					Paste your Gemini API key, drop in some content, and generate a two-host audio
					podcast. Your key stays in your browser — it's only sent to{" "}
					<code>api.google.com</code>. Powered by{" "}
					<a href="https://github.com/Nitzan94/gemini-podcast" style={styles.link}>
						gemini-podcast
					</a>{" "}
					(MIT).
				</p>
			</header>

			<section style={styles.section}>
				<h2 style={styles.h2}>1. API key</h2>
				<input
					type="password"
					placeholder="AIza…"
					value={apiKey}
					onChange={(e) => setApiKey(e.target.value)}
					style={styles.input}
					autoComplete="off"
					spellCheck={false}
				/>
				<label style={styles.checkboxRow}>
					<input
						type="checkbox"
						checked={rememberKey}
						onChange={(e) => setRememberKey(e.target.checked)}
					/>
					Remember in this browser (localStorage)
				</label>
				<p style={styles.hint}>
					Get one at{" "}
					<a href="https://aistudio.google.com/apikey" style={styles.link}>
						aistudio.google.com/apikey
					</a>
					.
				</p>
			</section>

			<section style={styles.section}>
				<h2 style={styles.h2}>2. Subject + source material</h2>
				<label style={styles.label}>Subject (one line)</label>
				<input
					value={subject}
					onChange={(e) => setSubject(e.target.value)}
					style={styles.input}
					placeholder={SAMPLE_SUBJECT}
				/>

				{sections.map((s, i) => (
					<div key={i} style={styles.sectionCard}>
						<div style={styles.sectionHeader}>
							<input
								value={s.title}
								onChange={(e) => updateSection(i, { title: e.target.value })}
								placeholder={`Section ${i + 1} title`}
								style={styles.sectionTitleInput}
							/>
							{sections.length > 1 && (
								<button
									type="button"
									onClick={() => removeSection(i)}
									style={styles.buttonGhost}
									aria-label="Remove section"
								>
									remove
								</button>
							)}
						</div>
						<textarea
							value={s.content}
							onChange={(e) => updateSection(i, { content: e.target.value })}
							placeholder="Paste content here — a few paragraphs, ~200–800 words works best."
							rows={6}
							style={styles.textarea}
						/>
					</div>
				))}
				<button type="button" onClick={addSection} style={styles.buttonSecondary}>
					+ Add section
				</button>
			</section>

			<section style={styles.section}>
				<h2 style={styles.h2}>3. Hosts</h2>
				<div style={styles.row}>
					<div style={styles.col}>
						<label style={styles.label}>Host A name</label>
						<input
							value={hostAName}
							onChange={(e) => setHostAName(e.target.value)}
							style={styles.input}
						/>
						<label style={styles.hint}>
							Voice: <code>{pair.voiceA}</code>
						</label>
					</div>
					<div style={styles.col}>
						<label style={styles.label}>Host B name</label>
						<input
							value={hostBName}
							onChange={(e) => setHostBName(e.target.value)}
							style={styles.input}
						/>
						<label style={styles.hint}>
							Voice: <code>{pair.voiceB}</code>
						</label>
					</div>
				</div>
				<label style={styles.label}>Voice pair</label>
				<select
					value={pairIdx}
					onChange={(e) => setPairIdx(Number(e.target.value))}
					style={styles.input}
				>
					{VOICE_PAIRS.map((p, i) => (
						<option key={p.voiceA + p.voiceB} value={i}>
							{p.voiceA} & {p.voiceB} — {p.descriptor}
						</option>
					))}
				</select>
				<label style={styles.label}>Persona hint (optional)</label>
				<input
					value={personaHint}
					onChange={(e) => setPersonaHint(e.target.value)}
					style={styles.input}
					placeholder="e.g. two history-curious explainers, dry not breathless"
				/>
			</section>

			<section style={styles.section}>
				<button
					type="button"
					onClick={onGenerate}
					disabled={isRunning}
					style={isRunning ? styles.buttonDisabled : styles.buttonPrimary}
				>
					{isRunning ? "Generating…" : "Generate podcast"}
				</button>
				<p style={styles.hint}>
					Typical end-to-end: 30–90 seconds depending on dialogue length. Uses the Pro model
					for script + Flash TTS preview.
				</p>

				{status.kind === "running" && (
					<div style={styles.statusRunning}>
						<div style={styles.spinner} />
						<span>{status.detail}</span>
					</div>
				)}
				{status.kind === "error" && (
					<div style={styles.statusError}>
						<strong>Error:</strong> {status.message}
					</div>
				)}
				{status.kind === "done" && (
					<div style={styles.statusDone}>
						<audio controls src={status.url} style={styles.audio} />
						<div style={styles.row}>
							<a href={status.url} download="podcast.wav" style={styles.buttonSecondary}>
								Download WAV
							</a>
							<span style={styles.hint}>
								{(status.bytes / 1024 / 1024).toFixed(1)} MB · {status.turns.length} turns
								· script {status.durations.scriptGen}ms · TTS{" "}
								{status.durations.synthesize}ms
							</span>
						</div>
						<details style={styles.transcript}>
							<summary>Show transcript</summary>
							<div style={styles.transcriptBody}>
								{status.turns.map((t, i) => (
									<p key={i}>
										<strong>{t.speaker}:</strong> {t.text}
									</p>
								))}
							</div>
						</details>
					</div>
				)}
			</section>

			<footer style={styles.footer}>
				<p>
					Open source on{" "}
					<a href="https://github.com/Nitzan94/gemini-podcast" style={styles.link}>
						GitHub
					</a>
					. Python package at <code>pip install gemini-podcast</code>.
				</p>
			</footer>
		</div>
	);
}

const styles = {
	page: {
		maxWidth: 760,
		margin: "0 auto",
		padding: "40px 20px 80px",
		fontFamily:
			"-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
		color: "#1B3926",
		lineHeight: 1.5,
	},
	header: { marginBottom: 32 },
	title: { fontSize: 28, margin: "0 0 8px", fontWeight: 700 },
	subtitle: { color: "#4b5e54", margin: 0, fontSize: 15 },
	link: { color: "#1B3926", textDecoration: "underline" },
	section: {
		background: "#fff",
		border: "1px solid rgba(27, 57, 38, 0.12)",
		borderRadius: 10,
		padding: 20,
		marginBottom: 16,
	},
	h2: { fontSize: 16, margin: "0 0 12px", fontWeight: 600 },
	input: {
		width: "100%",
		padding: "10px 12px",
		border: "1px solid rgba(27, 57, 38, 0.18)",
		borderRadius: 6,
		fontSize: 14,
		fontFamily: "inherit",
		boxSizing: "border-box" as const,
		background: "#fff",
		color: "inherit",
	},
	textarea: {
		width: "100%",
		padding: "10px 12px",
		border: "1px solid rgba(27, 57, 38, 0.18)",
		borderRadius: 6,
		fontSize: 14,
		fontFamily: "inherit",
		boxSizing: "border-box" as const,
		background: "#fff",
		color: "inherit",
		resize: "vertical" as const,
	},
	label: { display: "block", margin: "12px 0 6px", fontSize: 13, fontWeight: 500 },
	hint: { color: "#7a8a82", fontSize: 12, margin: "6px 0" },
	checkboxRow: {
		display: "flex",
		alignItems: "center",
		gap: 6,
		margin: "8px 0 0",
		fontSize: 13,
	},
	sectionCard: {
		marginTop: 12,
		padding: 12,
		background: "#F7F4EC",
		border: "1px solid rgba(27, 57, 38, 0.08)",
		borderRadius: 6,
	},
	sectionHeader: { display: "flex", gap: 8, marginBottom: 8 },
	sectionTitleInput: {
		flex: 1,
		padding: "8px 10px",
		border: "1px solid rgba(27, 57, 38, 0.18)",
		borderRadius: 6,
		fontSize: 14,
		fontFamily: "inherit",
		fontWeight: 600,
		background: "#fff",
	},
	row: { display: "flex", gap: 12, marginTop: 10, flexWrap: "wrap" as const },
	col: { flex: 1, minWidth: 180 },
	buttonPrimary: {
		padding: "12px 20px",
		background: "#1B3926",
		color: "#fff",
		border: "none",
		borderRadius: 6,
		fontSize: 14,
		fontWeight: 600,
		cursor: "pointer",
	},
	buttonDisabled: {
		padding: "12px 20px",
		background: "#7a8a82",
		color: "#fff",
		border: "none",
		borderRadius: 6,
		fontSize: 14,
		fontWeight: 600,
		cursor: "not-allowed",
	},
	buttonSecondary: {
		padding: "8px 14px",
		background: "#fff",
		color: "#1B3926",
		border: "1px solid #1B3926",
		borderRadius: 6,
		fontSize: 13,
		fontWeight: 500,
		cursor: "pointer",
		display: "inline-block",
		textDecoration: "none",
	},
	buttonGhost: {
		padding: "4px 10px",
		background: "transparent",
		color: "#b0412b",
		border: "none",
		borderRadius: 4,
		fontSize: 12,
		cursor: "pointer",
	},
	statusRunning: {
		marginTop: 14,
		display: "flex",
		alignItems: "center",
		gap: 10,
		padding: 12,
		background: "#F7F4EC",
		borderRadius: 6,
		fontSize: 14,
	},
	spinner: {
		width: 14,
		height: 14,
		border: "2px solid rgba(27,57,38,0.2)",
		borderTopColor: "#1B3926",
		borderRadius: "50%",
		animation: "spin 0.8s linear infinite",
	},
	statusError: {
		marginTop: 14,
		padding: 12,
		background: "#fdebe5",
		color: "#7a2510",
		borderRadius: 6,
		fontSize: 14,
	},
	statusDone: {
		marginTop: 14,
		padding: 14,
		background: "#eaf3ec",
		borderRadius: 6,
	},
	audio: { width: "100%", marginBottom: 10 },
	transcript: { marginTop: 12 },
	transcriptBody: {
		maxHeight: 280,
		overflowY: "auto" as const,
		marginTop: 8,
		padding: 12,
		background: "#fff",
		border: "1px solid rgba(27,57,38,0.1)",
		borderRadius: 6,
		fontSize: 13,
	},
	footer: {
		marginTop: 32,
		paddingTop: 20,
		borderTop: "1px solid rgba(27, 57, 38, 0.08)",
		color: "#7a8a82",
		fontSize: 13,
		textAlign: "center" as const,
	},
};
