import React, { useState, useRef, useEffect, useCallback } from 'react';
import { AppState, DocumentChunk, ChatMessage, AVAILABLE_VOICES, Language, VoiceOption } from './types';
import { extractTextFromDocument, translateText, generateSpeech, generateEmbeddings, answerQuestionWithRAG, transcribeAudio } from './services/geminiService';
import { pcmToWav, decodeBase64 } from './utils/audioUtils';

// Add type for marked
declare global {
  interface Window {
    marked: {
      parse: (text: string) => string;
    };
  }
}

// Robust Markdown rendering using marked.js
const MarkdownView = ({ text }: { text: string }) => {
  const [html, setHtml] = useState("");

  useEffect(() => {
    if (window.marked) {
      setHtml(window.marked.parse(text));
    } else {
      setHtml(text); // Fallback if marked fails
    }
  }, [text]);

  return (
    <div 
      className="markdown-content font-serif text-lg leading-relaxed text-gray-800"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
};

// Chat Bubble Markdown (Simplified for small text)
const ChatMarkdown = ({ text }: { text: string }) => {
   const [html, setHtml] = useState("");
   useEffect(() => {
     if (window.marked) {
        // Simple config for chat
       setHtml(window.marked.parse(text));
     } else {
       setHtml(text);
     }
   }, [text]);
   
   return <div className="prose prose-sm max-w-none text-inherit [&>p]:mb-2 [&>p:last-child]:mb-0" dangerouslySetInnerHTML={{ __html: html }} />;
}

const App: React.FC = () => {
  const [appState, setAppState] = useState<AppState>(AppState.UPLOAD);
  const [uploadMode, setUploadMode] = useState<'file' | 'url'>('file');
  const [urlInput, setUrlInput] = useState("");
  const [docText, setDocText] = useState<string>("");
  const [originalDocText, setOriginalDocText] = useState<string>("");
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [loadingMsg, setLoadingMsg] = useState<string>("");
  
  // Audio State
  const [selectedVoice, setSelectedVoice] = useState<VoiceOption>(AVAILABLE_VOICES[2]); // Default Kore
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isGeneratingAudio, setIsGeneratingAudio] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);
  
  // Translation State
  const [currentLang, setCurrentLang] = useState<Language>(Language.ENGLISH);
  const [isTranslating, setIsTranslating] = useState(false);

  // Chat State
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isChatting, setIsChatting] = useState(false);

  // Voice Input State
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const [recordingMimeType, setRecordingMimeType] = useState<string>("");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  // Helper to find supported mime type
  const getSupportedMimeType = () => {
    const types = [
      'audio/webm',
      'audio/mp4',
      'audio/ogg',
      'audio/wav',
      'audio/webm;codecs=opus'
    ];
    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) {
        return type;
      }
    }
    return ''; // Fallback to browser default if none specific match
  };

  const handleProcessingSuccess = async (result: { displayedText: string; ragText: string }, isVideo: boolean) => {
    if (!result.displayedText || result.displayedText.length === 0) {
        throw new Error("Could not extract content.");
    }

    setDocText(result.displayedText);
    setOriginalDocText(result.displayedText);
    
    // 2. Prepare RAG (Background)
    setLoadingMsg("Creating intelligent search index...");
    
    // Prefer the ragText (transcript) for video RAG if it's substantial, otherwise use displayedText
    const textToChunk = (isVideo && result.ragText.length > 100) ? result.ragText : result.displayedText;
    
    // Split by double newline to get rough paragraphs
    const splitText = textToChunk.split(/\n\n+/).filter(t => t.length > 20);
    const embeddings = await generateEmbeddings(splitText);
    setChunks(embeddings);

    setAppState(AppState.INTERACTIVE);
  };

  const handleUrlSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlInput.trim()) return;

    setAppState(AppState.PROCESSING);
    setLoadingMsg(`Analyzing video content from URL in ${currentLang}...`);

    try {
        // Pass null for base64Data, and a dummy video mimeType just to trigger video logic if needed, 
        // but explicit 'url' param handles the logic in service.
        const result = await extractTextFromDocument(null, 'video/mp4', false, currentLang, urlInput);
        await handleProcessingSuccess(result, true);
    } catch (err) {
        console.error(err);
        alert("Failed to analyze URL. Please ensure it is accessible.");
        setAppState(AppState.UPLOAD);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setAppState(AppState.PROCESSING);
    
    const isVideo = file.type.startsWith('video/');
    if (isVideo) {
      setLoadingMsg(`Watching video and writing notes in ${currentLang}...`);
    } else {
      setLoadingMsg("Reading document and formatting text...");
    }

    try {
      const reader = new FileReader();
      reader.onload = async (e) => {
        const base64Data = e.target?.result as string;
        const base64Content = base64Data.split(',')[1];
        
        // 1. Intelligent Extraction (with naive Fallback logic for docs)
        let result = await extractTextFromDocument(base64Content, file.type, false, currentLang);
        
        // "OCR Fallback": Only for documents where extraction yielded very little text
        if (!isVideo && result.displayedText.length < 50) {
           setLoadingMsg("Standard text extraction failed. Switching to Vision OCR...");
           result = await extractTextFromDocument(base64Content, file.type, true, currentLang);
        }

        await handleProcessingSuccess(result, isVideo);
      };
      reader.readAsDataURL(file);
    } catch (err) {
      console.error(err);
      alert("Failed to process file. It might be too large or unsupported.");
      setAppState(AppState.UPLOAD);
    }
  };

  const handleTranslate = async (lang: Language) => {
    if (lang === Language.ENGLISH && currentLang === Language.ENGLISH) return;
    
    setIsTranslating(true);
    try {
      const translated = await translateText(originalDocText, lang);
      setDocText(translated);
      setCurrentLang(lang);
    } catch (e) {
      alert("Translation failed");
    } finally {
      setIsTranslating(false);
    }
  };

  const handleGenerateAudio = async () => {
    setIsGeneratingAudio(true);
    try {
      // Changed: service now handles chunking and returns complete Uint8Array buffer
      const rawBytes = await generateSpeech(docText, selectedVoice.name);
      
      const wavBlob = pcmToWav(rawBytes);
      const url = URL.createObjectURL(wavBlob);
      setAudioUrl(url);
    } catch (e) {
      alert("Audio generation failed");
    } finally {
      setIsGeneratingAudio(false);
    }
  };

  const handleSendMessage = async () => {
    if (!chatInput.trim() || isChatting) return;

    // Feature: Real-time Control - Pause audio when querying
    if (audioRef.current && !audioRef.current.paused) {
      audioRef.current.pause();
    }

    const userMsg: ChatMessage = { id: Date.now().toString(), role: 'user', text: chatInput, timestamp: Date.now() };
    setChatHistory(prev => [...prev, userMsg]);
    setChatInput("");
    setIsChatting(true);

    try {
      const answer = await answerQuestionWithRAG(userMsg.text, chunks);
      const modelMsg: ChatMessage = { id: (Date.now() + 1).toString(), role: 'model', text: answer, timestamp: Date.now() };
      setChatHistory(prev => [...prev, modelMsg]);
    } catch (e) {
      setChatHistory(prev => [...prev, { id: Date.now().toString(), role: 'model', text: "Sorry, I encountered an error.", timestamp: Date.now() }]);
    } finally {
      setIsChatting(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      const mimeType = getSupportedMimeType();
      setRecordingMimeType(mimeType);

      const options = mimeType ? { mimeType } : undefined;
      const mediaRecorder = new MediaRecorder(stream, options);
      
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType || 'audio/webm' });
        
        const reader = new FileReader();
        reader.readAsDataURL(audioBlob);
        reader.onloadend = async () => {
          const base64Audio = (reader.result as string).split(',')[1];
          setIsTranscribing(true);
          try {
            const text = await transcribeAudio(base64Audio, mimeType || 'audio/webm');
            setChatInput(text);
          } catch (e) {
            console.error("Transcription error:", e);
            alert("Could not transcribe audio.");
          } finally {
            setIsTranscribing(false);
          }
        };

        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      
      if (audioRef.current && !audioRef.current.paused) {
        audioRef.current.pause();
      }

    } catch (err) {
      console.error("Error accessing microphone:", err);
      alert("Microphone access denied or not available.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-amber-50 to-yellow-50 flex flex-col font-sans text-gray-900">
      {/* Header */}
      <header className="bg-gradient-to-r from-orange-600 to-amber-600 border-b border-orange-700/20 sticky top-0 z-30 shadow-lg backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 md:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center text-white text-xl shadow-lg">
              <i className="fa-solid fa-book-open-reader"></i>
            </div>
            <div className="flex flex-col">
              <h1 className="text-xl font-bold tracking-tight text-white leading-tight">ARIA</h1>
              <span className="text-xs font-medium text-orange-100 uppercase tracking-wider">Automated Reading Interactive Assistant</span>
            </div>
          </div>
          {appState === AppState.INTERACTIVE && (
             <button 
             type="button"
             onClick={() => {
                // Reset everything to go back to upload state
                setAppState(AppState.UPLOAD);
                setDocText("");
                setOriginalDocText("");
                setChunks([]);
                setAudioUrl(null);
                setChatHistory([]);
                setUrlInput("");
                setUploadMode('file');
                setLoadingMsg("");
             }}
             className="text-sm font-medium text-white/90 hover:text-white transition-colors px-3 py-2 rounded-lg hover:bg-white/10 flex items-center gap-2">
             <i className="fa-solid fa-plus"></i>
             <span className="hidden sm:inline">New Project</span>
           </button>
          )}
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full p-4 md:p-6 fade-in">
        
        {/* Upload State */}
        {appState === AppState.UPLOAD && (
          <div className="min-h-[60vh] flex flex-col items-center justify-center gap-8 py-10 animate-fade-in-up">
            
            <div className="text-center max-w-2xl mx-auto mb-4">
              <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">Transform Content into Knowledge</h2>
              <p className="text-lg text-gray-600">Upload documents, images, or videos. Gemini will summarize, note-take, and narrate them for you.</p>
            </div>

            <div className="bg-white p-1.5 rounded-xl shadow-md border border-orange-200 flex mb-2">
                <button 
                  type="button"
                  onClick={() => setUploadMode('file')}
                  className={`px-6 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 flex items-center gap-2 ${uploadMode === 'file' ? 'bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-md' : 'text-gray-600 hover:text-gray-900 hover:bg-orange-50'}`}
                >
                  <i className="fa-solid fa-cloud-arrow-up"></i> Upload File
                </button>
                <button 
                  type="button"
                  onClick={() => setUploadMode('url')}
                  className={`px-6 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 flex items-center gap-2 ${uploadMode === 'url' ? 'bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-md' : 'text-gray-600 hover:text-gray-900 hover:bg-orange-50'}`}
                >
                  <i className="fa-solid fa-link"></i> Paste URL
                </button>
            </div>

            {uploadMode === 'file' ? (
              <div className="w-full max-w-xl aspect-[3/2] md:aspect-[2/1] border-2 border-dashed border-orange-300 rounded-3xl bg-white hover:border-orange-500 hover:bg-gradient-to-br hover:from-orange-50 hover:to-amber-50 transition-all duration-300 cursor-pointer relative overflow-hidden group shadow-lg hover:shadow-xl">
                <input 
                  type="file" 
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  accept="image/png, image/jpeg, image/jpg, application/pdf, video/mp4, video/quicktime, video/webm, video/avi"
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                />
                <div className="absolute inset-0 flex flex-col items-center justify-center p-8 pointer-events-none">
                  <div className="w-20 h-20 bg-gradient-to-br from-orange-100 to-amber-100 text-orange-600 rounded-full flex items-center justify-center mb-6 text-3xl group-hover:scale-110 group-hover:from-orange-200 group-hover:to-amber-200 transition-all duration-300 shadow-md">
                    <i className="fa-solid fa-cloud-arrow-up"></i>
                  </div>
                  <h3 className="text-xl font-semibold mb-2 text-gray-900">Drag & drop or click to upload</h3>
                  <p className="text-gray-600 text-sm mb-6">Supports PDF, Images (OCR), and Videos</p>
                  
                  <div className="flex gap-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                    <span className="bg-orange-100 text-orange-700 px-3 py-1 rounded-full"><i className="fa-solid fa-file-pdf mr-1"></i> PDF</span>
                    <span className="bg-orange-100 text-orange-700 px-3 py-1 rounded-full"><i className="fa-solid fa-file-image mr-1"></i> OCR</span>
                    <span className="bg-orange-100 text-orange-700 px-3 py-1 rounded-full"><i className="fa-solid fa-video mr-1"></i> Video</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="w-full max-w-xl bg-white p-8 rounded-3xl shadow-xl border border-orange-100">
                 <div className="w-16 h-16 bg-red-50 text-red-600 rounded-full flex items-center justify-center mx-auto mb-6 text-3xl shadow-sm">
                    <i className="fa-brands fa-youtube"></i>
                  </div>
                 <h3 className="text-xl font-semibold mb-6 text-center text-gray-900">Analyze Video from Web</h3>
                 <div className="flex gap-2">
                    <div className="relative flex-1">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <i className="fa-solid fa-link text-gray-400"></i>
                      </div>
                      <input 
                        type="url" 
                        required
                        placeholder="https://youtube.com/watch?v=..."
                        value={urlInput}
                        onChange={(e) => setUrlInput(e.target.value)}
                        className="w-full bg-white text-gray-900 border-2 border-orange-200 rounded-xl pl-10 pr-4 py-3 focus:ring-2 focus:ring-orange-500 focus:border-orange-500 outline-none transition-all placeholder:text-gray-400"
                      />
                    </div>
                    <button 
                      onClick={handleUrlSubmit}
                      className="bg-gradient-to-r from-orange-500 to-amber-500 text-white px-6 py-3 rounded-xl font-medium hover:from-orange-600 hover:to-amber-600 transition-all shadow-md hover:shadow-lg active:translate-y-0.5"
                    >
                      Analyze
                    </button>
                 </div>
                 <div className="mt-6 flex items-start gap-3 p-3 bg-amber-50 border-l-4 border-orange-500 rounded-lg text-sm text-gray-700">
                    <i className="fa-solid fa-circle-info mt-0.5 text-orange-600"></i>
                    <p>Paste a public URL. Gemini will search the web to find the video content, transcript, and metadata to generate comprehensive notes.</p>
                 </div>
              </div>
            )}

            <div className="flex items-center gap-3 bg-white px-5 py-3 rounded-xl shadow-md border border-orange-200 mt-4 hover:border-orange-400 transition-colors">
              <span className="text-sm font-medium text-gray-600">Output Language:</span>
              <select 
                value={currentLang}
                onChange={(e) => setCurrentLang(e.target.value as Language)}
                className="bg-transparent text-sm font-bold text-orange-600 outline-none cursor-pointer hover:text-orange-800"
              >
                {Object.values(Language).map(lang => (
                  <option key={lang} value={lang}>{lang}</option>
                ))}
              </select>
            </div>
          </div>
        )}

        {/* Processing State */}
        {appState === AppState.PROCESSING && (
          <div className="h-[70vh] flex flex-col items-center justify-center text-center">
             <div className="relative w-24 h-24 mb-8">
               <div className="absolute inset-0 border-4 border-orange-200 rounded-full"></div>
               <div className="absolute inset-0 border-4 border-orange-600 rounded-full border-t-transparent animate-spin"></div>
               <div className="absolute inset-0 flex items-center justify-center text-orange-600 text-2xl animate-pulse">
                 <i className="fa-solid fa-wand-magic-sparkles"></i>
               </div>
             </div>
            <h3 className="text-2xl font-bold text-gray-800 mb-2">Analyzing Content</h3>
            <p className="text-lg text-gray-600 font-medium animate-pulse">{loadingMsg}</p>
            <p className="text-sm text-gray-500 mt-4 max-w-md mx-auto">This usually takes 10-20 seconds depending on the file complexity. We are using Gemini 2.5 Flash & 3 Pro.</p>
          </div>
        )}

        {/* Interactive Workspace */}
        {appState === AppState.INTERACTIVE && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-7rem)] min-h-[600px]">
            
            {/* Left: Document View (Reader) */}
            <div className="lg:col-span-7 bg-white rounded-2xl shadow-xl border border-orange-100 flex flex-col overflow-hidden relative">
              {/* Toolbar */}
              <div className="px-6 py-4 border-b border-orange-100 flex items-center justify-between bg-gradient-to-r from-orange-50 to-amber-50 backdrop-blur-sm sticky top-0 z-10">
                <div className="flex items-center gap-3">
                  <div className="relative group">
                    <select 
                      value={currentLang}
                      onChange={(e) => handleTranslate(e.target.value as Language)}
                      disabled={isTranslating}
                      className="appearance-none bg-white border-2 border-orange-200 hover:border-orange-400 text-gray-700 text-sm font-medium rounded-lg pl-3 pr-8 py-2 focus:ring-2 focus:ring-orange-500 outline-none transition-all cursor-pointer disabled:opacity-50 shadow-sm"
                    >
                      {Object.values(Language).map(lang => (
                        <option key={lang} value={lang}>{lang}</option>
                      ))}
                    </select>
                    <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-orange-600">
                      <i className="fa-solid fa-language"></i>
                    </div>
                  </div>
                  {isTranslating && <span className="text-xs text-orange-600 font-medium animate-pulse">Translating...</span>}
                </div>
                
                <div className="flex items-center gap-3">
                   <div className="flex items-center gap-2 bg-white rounded-lg p-1 border-2 border-orange-200 shadow-sm">
                      <span className="text-xs font-semibold text-gray-500 px-2 uppercase">Voice</span>
                      <select
                        value={selectedVoice.name}
                        onChange={(e) => {
                          const v = AVAILABLE_VOICES.find(x => x.name === e.target.value);
                          if(v) setSelectedVoice(v);
                        }}
                        className="bg-transparent text-sm font-medium text-gray-700 outline-none w-24 sm:w-28 cursor-pointer"
                      >
                        {AVAILABLE_VOICES.map(v => (
                          <option key={v.name} value={v.name}>{v.label}</option>
                        ))}
                      </select>
                   </div>
                   
                   {!audioUrl && (
                     <button 
                      onClick={handleGenerateAudio}
                      disabled={isGeneratingAudio}
                      className="bg-gradient-to-r from-orange-500 to-amber-500 text-white text-sm font-medium px-4 py-2 rounded-lg hover:from-orange-600 hover:to-amber-600 shadow-md hover:shadow-lg transition-all disabled:opacity-70 disabled:cursor-not-allowed flex items-center gap-2"
                     >
                       {isGeneratingAudio ? <i className="fa-solid fa-circle-notch fa-spin"></i> : <i className="fa-solid fa-headphones"></i>}
                       <span className="hidden sm:inline">Narrate</span>
                     </button>
                   )}
                </div>
              </div>

              {/* Text Content */}
              <div className="flex-1 overflow-y-auto px-8 py-8 md:px-10 bg-white scroll-smooth">
                <article className="max-w-none">
                  <MarkdownView text={docText} />
                </article>
                <div className="h-24"></div> {/* Bottom spacer for player */}
              </div>

              {/* Floating Audio Player */}
              {audioUrl && (
                <div className="absolute bottom-6 left-1/2 -translate-x-1/2 w-[90%] md:w-[80%] bg-gradient-to-r from-gray-900 to-gray-800 backdrop-blur-md text-white rounded-2xl shadow-2xl p-3 border border-orange-500/30 flex items-center gap-4 transition-all hover:scale-[1.01]">
                   <button 
                     onClick={() => {
                       if(audioRef.current) audioRef.current.paused ? audioRef.current.play() : audioRef.current.pause();
                    }} 
                    className="w-12 h-12 rounded-full bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 flex items-center justify-center text-white text-xl transition-all shadow-lg shrink-0"
                   >
                      <i className="fa-solid fa-play pl-1"></i>
                   </button>
                   
                   <div className="flex-1 min-w-0 flex flex-col justify-center h-full">
                      <span className="text-xs text-orange-300 mb-1">Now Playing • {selectedVoice.label}</span>
                      <audio 
                        ref={audioRef}
                        id="main-audio" 
                        controls 
                        src={audioUrl} 
                        className="w-full h-8 opacity-80 hover:opacity-100 transition-opacity" 
                      />
                   </div>

                   <a href={audioUrl} download="audiobook.wav" className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-white/10 text-gray-400 hover:text-white transition-colors shrink-0" title="Download Audio">
                      <i className="fa-solid fa-download"></i>
                   </a>
                </div>
              )}
            </div>

            {/* Right: RAG Chat */}
            <div className="lg:col-span-5 flex flex-col bg-white rounded-2xl shadow-xl border border-orange-100 overflow-hidden">
              <div className="p-4 border-b border-orange-100 bg-gradient-to-r from-orange-50 to-amber-50 flex items-center justify-between">
                <div>
                  <h2 className="font-bold text-gray-800 flex items-center gap-2">
                    <i className="fa-solid fa-sparkles text-orange-600"></i>
                    AI Companion
                  </h2>
                  <p className="text-xs text-gray-600">Ask questions about the content</p>
                </div>
                {/* Visual Indicator for paused audio */}
                {audioRef.current && !audioRef.current.paused && (
                   <span className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded-full animate-pulse">
                     <i className="fa-solid fa-volume-high mr-1"></i> Audio Active
                   </span>
                )}
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-5 bg-gradient-to-br from-orange-50/30 to-amber-50/30">
                {chatHistory.length === 0 && (
                  <div className="flex flex-col items-center justify-center h-full text-center text-gray-400 p-8">
                    <div className="w-16 h-16 bg-gradient-to-br from-orange-100 to-amber-100 text-orange-600 rounded-full flex items-center justify-center mb-4 text-2xl shadow-sm">
                      <i className="fa-regular fa-comments"></i>
                    </div>
                    <p className="font-medium text-gray-600 mb-1">No questions yet</p>
                    <p className="text-sm">Ask about key topics, summaries, or specific details from your document.</p>
                  </div>
                )}
                
                {chatHistory.map(msg => (
                  <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in-up`}>
                    
                    {msg.role === 'model' && (
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-orange-500 to-amber-600 flex items-center justify-center text-white text-xs shrink-0 mr-2 mt-1 shadow-md">
                        <i className="fa-solid fa-wand-magic-sparkles"></i>
                      </div>
                    )}

                    <div className={`max-w-[85%] rounded-2xl px-5 py-3.5 text-sm shadow-sm leading-relaxed ${
                      msg.role === 'user' 
                        ? 'bg-gradient-to-r from-orange-500 to-amber-500 text-white rounded-br-sm' 
                        : 'bg-white text-gray-800 border border-orange-100 rounded-bl-sm'
                    }`}>
                      {msg.role === 'model' ? <ChatMarkdown text={msg.text} /> : msg.text}
                    </div>
                    
                    {msg.role === 'user' && (
                       <div className="w-8 h-8 rounded-full bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center text-gray-600 text-xs shrink-0 ml-2 mt-1 shadow-sm">
                         <i className="fa-solid fa-user"></i>
                       </div>
                    )}
                  </div>
                ))}
                
                {isChatting && (
                   <div className="flex justify-start">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-orange-500 to-amber-600 flex items-center justify-center text-white text-xs shrink-0 mr-2 shadow-md">
                        <i className="fa-solid fa-wand-magic-sparkles"></i>
                    </div>
                    <div className="bg-white border border-orange-100 rounded-2xl px-4 py-3 rounded-bl-sm flex gap-1.5 items-center shadow-sm">
                       <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce"></div>
                       <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce delay-100"></div>
                       <div className="w-2 h-2 bg-orange-500 rounded-full animate-bounce delay-200"></div>
                    </div>
                   </div>
                )}
                <div ref={chatEndRef}></div>
              </div>

              <div className="p-4 bg-white border-t border-orange-100">
                <div className="flex gap-2 relative">
                  <div className="relative flex-1 group">
                    <input
                      type="text"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      placeholder={isRecording ? "Listening..." : (isTranscribing ? "Processing audio..." : "Ask a question...")}
                      className={`w-full bg-orange-50 border-2 border-orange-200 rounded-xl pl-4 pr-12 py-3 text-sm focus:ring-2 focus:ring-orange-500 focus:bg-white focus:border-orange-400 outline-none transition-all ${isRecording ? 'ring-2 ring-red-500 bg-red-50 animate-pulse' : ''}`}
                      disabled={isRecording || isTranscribing}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSendMessage();
                        }
                      }}
                    />
                    
                    {/* Microphone Button */}
                    <button
                      type="button"
                      onClick={toggleRecording}
                      disabled={isTranscribing}
                      className={`absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center rounded-lg transition-all ${
                        isRecording 
                          ? "bg-red-500 text-white hover:bg-red-600 scale-105 shadow-md" 
                          : "text-gray-400 hover:text-orange-600 hover:bg-orange-100"
                      }`}
                      title={isRecording ? "Stop Recording" : "Voice Input"}
                    >
                      {isTranscribing ? (
                        <i className="fa-solid fa-circle-notch fa-spin text-orange-600"></i>
                      ) : (
                        <i className={`fa-solid ${isRecording ? 'fa-stop' : 'fa-microphone'}`}></i>
                      )}
                    </button>
                  </div>

                  <button 
                    onClick={handleSendMessage}
                    disabled={!chatInput.trim() || isChatting || isRecording}
                    className="w-12 h-12 flex items-center justify-center bg-gradient-to-r from-orange-500 to-amber-500 text-white hover:from-orange-600 hover:to-amber-600 rounded-xl transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:shadow-none disabled:cursor-not-allowed shrink-0 active:scale-95"
                  >
                    <i className="fa-solid fa-paper-plane"></i>
                  </button>
                </div>
              </div>
            </div>

          </div>
        )}
      </main>
    </div>
  );
};

export default App;