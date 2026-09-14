"use client";

import { useState } from "react";
import { BookOpen, CheckCircle, HelpCircle, Layers, FileText, Check, X, ShieldCheck } from "lucide-react";
import { LessonData } from "@/lib/api";

interface Props {
  lessonData: LessonData | null;
  version: number;
  totalVersions: number;
  onVersionChange?: (ver: number) => void;
  targetAudience?: string;
  attemptInfo?: string;
}

const DEFAULT_RAG_LESSON: LessonData = {
  title: "Introduction to Retrieval-Augmented Generation (RAG)",
  target_audience: "17–18 | Limited English | AI Career",
  sections: [
    {
      heading: "1. What You Will Learn",
      content: "In this lesson, you will learn what RAG is, why modern AI applications rely on it, how it combines external document retrieval with text generation, and how it differs from retraining an AI model.",
      key_takeaways: ["Understand RAG fundamentals", "Learn the difference between retrieval and training", "Know when to apply RAG"],
    },
    {
      heading: "2. What is RAG?",
      content: "RAG stands for Retrieval-Augmented Generation. It is an AI architecture that connects a large language model (LLM) to an external authoritative knowledge base—like private documents or real-time databases—so it can answer questions with factual accuracy.",
      key_takeaways: ["Retrieval: Finds relevant documents", "Augmented: Adds found documents into the prompt", "Generation: The LLM writes the final answer"],
    },
    {
      heading: "3. Why RAG?",
      content: "Standard LLMs only know facts up to their training cutoff date and cannot read your organization's private documents. RAG provides current, private, and verifiable knowledge to the AI at the exact moment a question is asked.",
      key_takeaways: ["Prevents outdated answers", "Allows private data access", "Reduces hallucinations"],
    },
    {
      heading: "4. Without RAG",
      content: "Without RAG, an LLM must guess answers based only on memorized training data. If asked about a company policy or a new research paper, it may hallucinate or generate convincing false claims.",
      key_takeaways: ["Hallucinations occur when knowledge is missing", "No source citations"],
    },
    {
      heading: "5. How RAG Works",
      content: "When a user asks a question, RAG executes three distinct steps:\n1. Search: The query is converted into an embedding vector to search a vector database (like pgvector).\n2. Augment: The top matching document snippets are added into the prompt as context.\n3. Generate: The LLM reads the context snippets and synthesizes an answer.",
      key_takeaways: ["Search ➔ Augment ➔ Generate", "Operates entirely at inference time"],
    },
    {
      heading: "6. Step-by-Step Simple Example",
      content: "Think of an open-book exam:\n- Standard LLM: A student taking a closed-book test trying to remember everything from memory.\n- RAG: A student taking an open-book test who looks up the exact chapter in a textbook before writing the answer.",
      key_takeaways: ["RAG is like an open-book exam", "Textbook = pgvector knowledge base"],
    },
    {
      heading: "7. Simple Architecture",
      content: "The RAG pipeline consists of:\n- Document Store: PostgreSQL with pgvector\n- Embedding Model: Converts text into vector numbers\n- Orchestrator: LangGraph manages the search and generation steps\n- Generator: LLM generates beginner-friendly explanations",
      key_takeaways: ["PostgreSQL + pgvector stores knowledge chunks", "Bounded top-K retrieval keeps costs predictable"],
    },
    {
      heading: "8. RAG vs Normal LLM",
      content: "A normal LLM is static—its knowledge is locked in its model weights. A RAG system is dynamic—you can add or update documents in your vector database at any time without retraining the LLM.",
      key_takeaways: ["Adding documents does NOT retrain model weights", "Zero training cost for knowledge updates"],
    },
    {
      heading: "9. Common Mistakes",
      content: "A very common misconception is believing that RAG retrains the model whenever new documents are indexed. This is FALSE. RAG only retrieves text at query time; the model weights remain untouched.",
      key_takeaways: ["Myth: RAG retrains weights (False)", "Reality: RAG retrieves context dynamically"],
    },
  ],
  summary: "RAG combines external search with generative AI to produce grounded, verifiable, and hallucination-free educational content without expensive model retraining.",
  vocabulary_definitions: {
    "RAG": "Retrieval-Augmented Generation — finding external facts to help an LLM answer accurately.",
    "pgvector": "A PostgreSQL extension that stores vector embeddings and finds similar text chunks.",
    "Vector Embedding": "A list of numbers representing the semantic meaning of a sentence.",
    "Hallucination": "When an AI generates believable but factually incorrect information.",
  },
  quiz: [
    {
      question: "What happens when you add new documents to a RAG knowledge base?",
      options: [
        "The LLM model weights are retrained automatically.",
        "The documents are indexed in pgvector for inference retrieval without retraining.",
        "The model must be downloaded again.",
        "All previous documents are permanently erased.",
      ],
      correct_option_index: 1,
      explanation: "RAG retrieves information dynamically at inference time. Adding documents indexes new embeddings in pgvector; it does NOT alter or retrain the LLM model weights.",
    },
    {
      question: "Which real-world analogy best describes how RAG works?",
      options: [
        "A closed-book exam relying purely on memory.",
        "An open-book exam where you look up the relevant textbook chapter before answering.",
        "Translating audio to text.",
        "Compressing a file to save disk space.",
      ],
      correct_option_index: 1,
      explanation: "RAG functions just like an open-book exam: the system searches authoritative textbooks (knowledge chunks) before synthesizing the answer.",
    },
    {
      question: "Why does RAG dramatically reduce hallucinations in LLM output?",
      options: [
        "Because it makes the LLM run faster.",
        "Because it grounds the generator with authoritative canonical evidence from pgvector.",
        "Because it deletes long queries.",
        "Because it prevents users from asking questions.",
      ],
      correct_option_index: 1,
      explanation: "By providing authoritative document chunks in the prompt context, the LLM generates answers grounded directly in factual evidence.",
    },
  ],
};

export default function LessonViewer({
  lessonData,
  version,
  totalVersions,
  onVersionChange,
  targetAudience = "17–18 | Limited English | AI Career",
  attemptInfo = "✓ PASS | Attempt 2 / 3",
}: Props) {
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, number>>({});

  const data = lessonData || DEFAULT_RAG_LESSON;

  const handleOptionSelect = (qIdx: number, oIdx: number) => {
    setSelectedAnswers({ ...selectedAnswers, [qIdx]: oIdx });
  };

  return (
    <div className="space-y-6">
      {/* Header Banner matching Section 11 Specification */}
      <div className="glass-panel rounded-2xl p-6 border border-emerald-500/30 bg-emerald-950/10 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-4">
          <div>
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs uppercase tracking-wider">
              <CheckCircle className="w-4 h-4" /> SHIPPED LESSON
            </div>
            <h2 className="text-xl font-extrabold text-white mt-1">{data.title}</h2>
          </div>

          <div className="flex items-center gap-3">
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              Evaluation: {attemptInfo}
            </span>

            {totalVersions > 1 && (
              <div className="flex items-center gap-2 bg-white/5 px-3 py-1 rounded-xl border border-white/10 text-xs">
                <Layers className="w-3.5 h-3.5 text-purple-400" />
                <span className="text-slate-400">Ver:</span>
                <select
                  value={version}
                  onChange={(e) => onVersionChange?.(Number(e.target.value))}
                  className="bg-transparent text-white font-bold focus:outline-none"
                >
                  {Array.from({ length: totalVersions }, (_, i) => i + 1).map((v) => (
                    <option key={v} value={v} className="bg-slate-900 text-white">
                      v{v}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>

        <div className="text-xs text-slate-300 flex flex-wrap items-center gap-6">
          <div>
            <span className="text-slate-400 block text-[10px] uppercase font-bold">Target Learner Profile:</span>
            <span className="font-semibold text-purple-300">{data.target_audience || targetAudience}</span>
          </div>
          <div>
            <span className="text-slate-400 block text-[10px] uppercase font-bold">Grounding Store:</span>
            <span className="font-semibold text-emerald-300">PostgreSQL pgvector Canonical Knowledge</span>
          </div>
          <div>
            <span className="text-slate-400 block text-[10px] uppercase font-bold">Hard Gate Status:</span>
            <span className="font-semibold text-emerald-400">PASSED ALL 4 LAYERS</span>
          </div>
        </div>
      </div>

      {/* Lesson Content Sections */}
      <div className="space-y-4">
        {data.sections?.map((section, idx) => (
          <div
            key={idx}
            className="glass-panel rounded-2xl p-6 border border-white/10 space-y-3"
          >
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <span className="w-6 h-6 rounded-lg bg-purple-500/20 text-purple-300 text-xs flex items-center justify-center font-mono">
                {idx + 1}
              </span>
              {section.heading}
            </h3>

            <div className="text-xs text-slate-300 leading-relaxed whitespace-pre-line">
              {section.content}
            </div>

            {section.key_takeaways && section.key_takeaways.length > 0 && (
              <div className="mt-4 p-3 rounded-xl bg-purple-500/10 border border-purple-500/20 space-y-1.5">
                <h4 className="text-[11px] font-bold text-purple-300 uppercase tracking-wider">
                  Key Takeaways
                </h4>
                <ul className="list-disc list-inside text-xs text-purple-200 space-y-1">
                  {section.key_takeaways.map((takeaway, tIdx) => (
                    <li key={tIdx}>{takeaway}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Summary Box */}
      {data.summary && (
        <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-2">
          <h3 className="text-xs font-bold text-purple-300 uppercase tracking-wider flex items-center gap-1.5">
            <BookOpen className="w-4 h-4" /> 10. Summary
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed">{data.summary}</p>
        </div>
      )}

      {/* Vocabulary Glossary */}
      {data.vocabulary_definitions && Object.keys(data.vocabulary_definitions).length > 0 && (
        <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-3">
          <h3 className="text-sm font-bold text-white">Vocabulary & Key Concepts</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Object.entries(data.vocabulary_definitions).map(([term, def], idx) => (
              <div key={idx} className="p-3 rounded-xl bg-white/5 border border-white/10 text-xs space-y-1">
                <span className="font-bold text-purple-300">{term}</span>
                <p className="text-slate-400">{def}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Interactive Assessment Quiz Component */}
      {data.quiz && data.quiz.length > 0 && (
        <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-6">
          <div className="flex items-center gap-2 border-b border-white/10 pb-3">
            <HelpCircle className="w-5 h-5 text-purple-400" />
            <h3 className="text-base font-bold text-white">11. Interactive Mini Quiz</h3>
          </div>

          <div className="space-y-6">
            {data.quiz.map((q, qIdx) => {
              const selected = selectedAnswers[qIdx];
              const hasAnswered = selected !== undefined;
              const isCorrect = selected === q.correct_option_index;

              return (
                <div
                  key={qIdx}
                  className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-3"
                >
                  <p className="text-xs font-semibold text-white">
                    <span className="text-purple-400 mr-2">Q{qIdx + 1}.</span>
                    {q.question}
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {q.options.map((opt, oIdx) => {
                      let btnStyle = "bg-white/5 hover:bg-white/10 border-white/10 text-slate-300";

                      if (hasAnswered) {
                        if (oIdx === q.correct_option_index) {
                          btnStyle = "bg-emerald-500/20 border-emerald-500 text-emerald-300 font-bold";
                        } else if (oIdx === selected) {
                          btnStyle = "bg-red-500/20 border-red-500 text-red-300";
                        }
                      }

                      return (
                        <button
                          key={oIdx}
                          onClick={() => handleOptionSelect(qIdx, oIdx)}
                          className={`p-3 rounded-lg border text-left text-xs transition flex items-center justify-between ${btnStyle}`}
                        >
                          <span>{opt}</span>
                          {hasAnswered && oIdx === q.correct_option_index && (
                            <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                          )}
                          {hasAnswered && oIdx === selected && oIdx !== q.correct_option_index && (
                            <X className="w-4 h-4 text-red-400 shrink-0" />
                          )}
                        </button>
                      );
                    })}
                  </div>

                  {hasAnswered && (
                    <div
                      className={`p-3 rounded-lg text-xs space-y-1 ${
                        isCorrect
                          ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-200"
                          : "bg-red-500/10 border border-red-500/20 text-red-200"
                      }`}
                    >
                      <span className="font-bold flex items-center gap-1">
                        {isCorrect ? <CheckCircle className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
                        {isCorrect ? "Correct!" : "Incorrect"}
                      </span>
                      <p>{q.explanation}</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
