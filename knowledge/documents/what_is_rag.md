# What is RAG (Retrieval-Augmented Generation)?

## Definition

RAG stands for **Retrieval-Augmented Generation**. It is a technique that combines information retrieval with text generation using a Large Language Model (LLM).

## Core Idea

Instead of relying only on what the LLM learned during its training, RAG **retrieves relevant information from external sources** (such as documents, databases, or knowledge bases) and provides this information to the LLM as additional context before generating a response.

## Key Points

- RAG does **NOT** retrain the LLM. The model's weights remain unchanged.
- RAG works by **retrieving** relevant documents and **injecting** them into the prompt as context.
- The LLM then generates a response that is **grounded** in the retrieved information.
- RAG is sometimes called "open-book exam" for AI — the model can look up information before answering.

## Simple Analogy

Think of RAG like a student taking an open-book exam. The student (LLM) already has some knowledge from studying (training). But during the exam, they can also look up information in their textbook (knowledge base) to give better, more accurate answers.

## Technical Summary

RAG = Retrieve relevant documents + Augment the prompt with retrieved context + Generate a response using the LLM

The LLM's parameters are never modified during RAG. Only the input prompt is augmented with additional context.
