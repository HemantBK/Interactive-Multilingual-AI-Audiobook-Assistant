import { GoogleGenAI, Modality, Type } from "@google/genai";
import { DocumentChunk, Language } from "../types";

// Initialize the client
const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

/**
 * Uses Gemini (gemini-3-pro-preview) to extract text from a document (Image or PDF)
 * OR generate a summary/notes from a video (File or URL).
 * Includes instructions for OCR fallback for scanned documents.
 * 
 * Returns:
 * - displayedText: The formatted markdown notes/summary to show in the UI.
 * - ragText: The text to use for RAG (embeddings). For videos, this is the transcript.
 */
export const extractTextFromDocument = async (
  base64Data: string | null, 
  mimeType: string, 
  forceOcr: boolean = false,
  targetLanguage: Language = Language.ENGLISH,
  url?: string
): Promise<{ displayedText: string; ragText: string }> => {
  try {
    const isVideo = mimeType.startsWith('video/') || !!url;
    let prompt = "";

    if (isVideo) {
      // Prompt for Video Summarization & Notes & Transcript
      prompt = `Analyze this video content thoroughly. 
      ${url ? `The video is located at this URL: ${url}` : ''}
      
      Role: You are an expert tutor creating study materials.
      
      Output format (Strict Markdown):
      1. **# Video Title/Topic** (H1)
      2. **## Executive Summary** (H2) - A concise, engaging paragraph.
      3. **## Key Takeaways** (H2) - A bulleted list of the most important points.
      4. **## Detailed Study Notes** (H2) - Structured with subheaders (###), bullet points, and bold text for emphasis.
      5. **## Timeline/Key Moments** (H2) - (Optional) If relevant.
      
      CRITICAL INSTRUCTION:
      After generating the study notes, output the separator "@@@TRANSCRIPT@@@" on a new line. 
      Then, provide a detailed transcript or comprehensive narrative of the video speech. 
      This transcript section will be used for answering user questions but hidden from the main view.
      
      Style Guidelines:
      - Use **bold** for key terms.
      - Ensure the layout is clean and readable.
      
      LANGUAGE REQUIREMENT:
      The entire output (Notes AND Transcript) MUST be generated in ${targetLanguage}.`;
    } else {
      // Prompt for Document OCR/Extraction
      prompt = forceOcr 
        ? `Perform strictly optical character recognition (OCR) on this document.
           
           Requirements:
           1. Extract every single word visible.
           2. Preserve the structure strictly using Markdown (headers #, lists -, bold **).
           3. CLEANUP: Exclude all page headers, footers, page numbers, and repetitive margin text.
           4. Remove any scanning noise or random artifacts.`
        : `Extract the main content from this document into clean, structured Markdown.
           If the document is a scanned PDF or image, perform OCR to capture all text.
           
           Formatting Rules:
           - Use Markdown headers (#, ##) for titles and sections.
           - Use bullet points (-) for lists.
           - Preserve bold/italic styling where visible.
           - Do not add conversational filler ("Here is the text..."), just output the document content.
           
           CLEANUP INSTRUCTIONS:
           - Remove page numbers (e.g., "Page 1 of 10").
           - Remove running headers and footers (e.g., "Confidential", "Annual Report 2024").
           - Fix broken line breaks within paragraphs.
           - Ignore artifacts or noise from scanning.
           - If it's a slide deck, organize it logically into sections.`;
    }

    const modelName = 'gemini-3-pro-preview';
    let requestOptions: any = {
      model: modelName,
      contents: { parts: [] }
    };

    // Construct parts based on input type (URL vs File)
    if (url) {
        requestOptions.contents.parts.push({ text: prompt });
        // Enable Google Search for URL processing
        requestOptions.config = {
            tools: [{ googleSearch: {} }]
        };
    } else if (base64Data) {
        requestOptions.contents.parts.push(
            {
                inlineData: {
                    mimeType: mimeType,
                    data: base64Data
                }
            },
            { text: prompt }
        );
    }

    const response = await ai.models.generateContent(requestOptions);
    
    let rawText = response.text || "";
    let displayedText = rawText;
    let ragText = rawText;

    // Handle Video Transcript Splitting
    if (isVideo) {
        const parts = rawText.split("@@@TRANSCRIPT@@@");
        if (parts.length > 1) {
            displayedText = parts[0].trim();
            // Use the hidden transcript for RAG
            ragText = parts[1].trim();
        }
        // If no separator found, ragText defaults to displayedText (notes)
    }

    // If search was used, append sources if available
    if (url && response.candidates?.[0]?.groundingMetadata?.groundingChunks) {
        const chunks = response.candidates[0].groundingMetadata.groundingChunks;
        const sources = chunks
            .flatMap((c: any) => c.web ? [`[${c.web.title}](${c.web.uri})`] : [])
            .join('\n- ');
        
        if (sources) {
            const sourceBlock = `\n\n### 🔗 Sources\n- ${sources}`;
            displayedText += sourceBlock;
            // Append sources to ragText as well so the AI knows where info came from
            ragText += sourceBlock; 
        }
    }

    return { displayedText, ragText };
  } catch (error) {
    console.error("Error extracting/processing content:", error);
    throw error;
  }
};

/**
 * Translates text to target language using gemini-2.5-flash
 */
export const translateText = async (text: string, targetLanguage: Language): Promise<string> => {
  try {
    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: `Translate the following markdown text into ${targetLanguage}. 
      
      Instructions:
      - Maintain ALL markdown formatting strictly (headers, bullets, bolding).
      - Do not translate code blocks or special identifiers.
      - Ensure natural phrasing in the target language.
      
      Text:\n${text}`
    });
    return response.text || "";
  } catch (error) {
    console.error("Error translating text:", error);
    throw error;
  }
};

/**
 * Generates Speech from text using gemini-2.5-flash-preview-tts
 * Supports long text by chunking requests and combining audio.
 */
export const generateSpeech = async (text: string, voiceName: string): Promise<Uint8Array> => {
  try {
    // Clean up markdown markers for TTS to avoid reading "Hash Hash Title"
    const cleanText = text
      .replace(/#{1,6}\s?/g, "") // Remove headers
      .replace(/\*\*/g, "")      // Remove bold
      .replace(/\*/g, "")        // Remove italics
      .replace(/`/g, "")         // Remove code ticks
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1") // Keep link text, remove URL
      .replace(/[-|_]{3,}/g, " ") // Remove horizontal rules
      .replace(/^\s*[-]\s+/gm, "") // Remove list bullets
      .replace(/\n{3,}/g, "\n\n"); // Normalize newlines

    // Chunking logic to handle long text (max ~3000 chars per chunk to be safe)
    const MAX_CHUNK_SIZE = 3000;
    const chunks: string[] = [];
    let currentPos = 0;

    while (currentPos < cleanText.length) {
      // If remaining text is small enough, take it all
      if (cleanText.length - currentPos <= MAX_CHUNK_SIZE) {
        chunks.push(cleanText.slice(currentPos));
        break;
      }

      let endPos = currentPos + MAX_CHUNK_SIZE;
      
      // Look for sentence terminators in the window to split cleanly
      const searchWindow = cleanText.slice(currentPos, endPos);
      const lastPeriod = searchWindow.lastIndexOf('.');
      const lastQuestion = searchWindow.lastIndexOf('?');
      const lastExclamation = searchWindow.lastIndexOf('!');
      const lastNewline = searchWindow.lastIndexOf('\n');
      
      const breakIndex = Math.max(lastPeriod, lastQuestion, lastExclamation, lastNewline);
      
      if (breakIndex !== -1) {
        // Include the punctuation in the chunk
        endPos = currentPos + breakIndex + 1;
      }
      
      chunks.push(cleanText.slice(currentPos, endPos).trim());
      currentPos = endPos;
    }

    const audioSegments: Uint8Array[] = [];

    // Process chunks sequentially
    for (const chunk of chunks) {
      if (!chunk.length) continue;

      const response = await ai.models.generateContent({
        model: "gemini-2.5-flash-preview-tts",
        contents: {
          parts: [{ text: chunk }]
        },
        config: {
          responseModalities: [Modality.AUDIO],
          speechConfig: {
            voiceConfig: {
              prebuiltVoiceConfig: { voiceName: voiceName }
            }
          }
        }
      });

      const audioDataBase64 = response.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
      if (audioDataBase64) {
        // Decode base64 to Uint8Array
        const binaryString = atob(audioDataBase64);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        audioSegments.push(bytes);
      }
    }
    
    if (audioSegments.length === 0) throw new Error("No audio data generated");
    
    // Concatenate all audio segments into one buffer
    const totalLength = audioSegments.reduce((sum, arr) => sum + arr.length, 0);
    const combinedAudio = new Uint8Array(totalLength);
    let offset = 0;
    for (const seg of audioSegments) {
      combinedAudio.set(seg, offset);
      offset += seg.length;
    }
    
    return combinedAudio;

  } catch (error) {
    console.error("Error generating speech:", error);
    throw error;
  }
};

/**
 * Transcribes audio input to text using gemini-2.5-flash
 */
export const transcribeAudio = async (base64Audio: string, mimeType: string): Promise<string> => {
  try {
    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: {
        parts: [
          {
            inlineData: {
              mimeType: mimeType,
              data: base64Audio
            }
          },
          { text: "Transcribe the audio exactly. Return only the text. Do not add timestamps." }
        ]
      }
    });
    return response.text || "";
  } catch (error) {
    console.error("Error transcribing audio:", error);
    throw error;
  }
};

/**
 * Generates embeddings for RAG using text-embedding-004
 */
export const generateEmbeddings = async (chunks: string[]): Promise<DocumentChunk[]> => {
  const resultChunks: DocumentChunk[] = [];
  
  // Embed in batches if needed, here we loop for simplicity in demo
  for (let i = 0; i < chunks.length; i++) {
    const chunkText = chunks[i];
    if (!chunkText.trim()) continue;

    try {
      const result = await ai.models.embedContent({
        model: "text-embedding-004",
        contents: chunkText
      });
      
      if (result.embeddings?.[0]?.values) {
        resultChunks.push({
          id: `chunk-${i}`,
          text: chunkText,
          embedding: result.embeddings[0].values
        });
      }
    } catch (e) {
      console.warn(`Failed to embed chunk ${i}`, e);
    }
  }

  return resultChunks;
};

/**
 * Answers questions using RAG context
 */
export const answerQuestionWithRAG = async (
  question: string, 
  contextChunks: DocumentChunk[]
): Promise<string> => {
  // 1. Embed Question
  const qEmbeddingResult = await ai.models.embedContent({
    model: "text-embedding-004",
    contents: question
  });
  const qEmbedding = qEmbeddingResult.embeddings?.[0]?.values;

  if (!qEmbedding) return "I couldn't process your question.";

  // 2. Find closest chunks (Cosine Similarity)
  const scoredChunks = contextChunks.map(chunk => {
    if (!chunk.embedding) return { ...chunk, score: -1 };
    const score = cosineSimilarity(qEmbedding, chunk.embedding);
    return { ...chunk, score };
  });

  // Sort by score descending
  scoredChunks.sort((a, b) => b.score - a.score);
  
  // Take top 3 relevant chunks
  const topChunks = scoredChunks.slice(0, 3);
  const contextText = topChunks.map(c => c.text).join("\n---\n");

  // 3. Generate Answer
  const response = await ai.models.generateContent({
    model: 'gemini-2.5-flash',
    contents: `You are a helpful study companion.
Use the provided context to answer the user's question clearly.
Format your answer with Markdown (bold key terms).
If the answer isn't in the context, say so politely.

Context:
${contextText}

Question: ${question}
`
  });

  return response.text || "I couldn't generate an answer.";
};

// Vector Utility
function cosineSimilarity(vecA: number[], vecB: number[]): number {
  let dotProduct = 0;
  let magnitudeA = 0;
  let magnitudeB = 0;
  for (let i = 0; i < vecA.length; i++) {
    dotProduct += vecA[i] * vecB[i];
    magnitudeA += vecA[i] * vecA[i];
    magnitudeB += vecB[i] * vecB[i];
  }
  magnitudeA = Math.sqrt(magnitudeA);
  magnitudeB = Math.sqrt(magnitudeB);
  if (magnitudeA === 0 || magnitudeB === 0) return 0;
  return dotProduct / (magnitudeA * magnitudeB);
}