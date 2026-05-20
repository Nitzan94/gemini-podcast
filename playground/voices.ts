// ABOUTME: TypeScript mirror of src/gemini_podcast/voices.py.
// ABOUTME: Keep this file in lockstep with the Python catalog when adding pairs.

export type VoicePair = {
	voiceA: string;
	voiceB: string;
	descriptor: string;
};

export const VOICE_PAIRS: readonly VoicePair[] = [
	{ voiceA: "Charon", voiceB: "Aoede", descriptor: "Informative + Breezy — NPR-style analyst & host" },
	{ voiceA: "Kore", voiceB: "Sulafat", descriptor: "Firm + Warm — anchor & approachable second" },
	{ voiceA: "Sadaltager", voiceB: "Achird", descriptor: "Knowledgeable + Friendly — expert & host" },
	{ voiceA: "Rasalgethi", voiceB: "Callirrhoe", descriptor: "Informative + Easy-going — casual explainer" },
	{ voiceA: "Orus", voiceB: "Laomedeia", descriptor: "Firm + Upbeat — energetic pairing" },
	{ voiceA: "Iapetus", voiceB: "Vindemiatrix", descriptor: "Clear + Gentle — calming long-form" },
	{ voiceA: "Gacrux", voiceB: "Sadachbia", descriptor: "Mature + Lively — older/younger contrast" },
	{ voiceA: "Algenib", voiceB: "Erinome", descriptor: "Gravelly + Clear — distinctive timbres" },
] as const;
