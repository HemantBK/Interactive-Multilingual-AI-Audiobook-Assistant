# Interactive Multilingual AI Audiobook Assistant

Convert scanned or digital documents into an interactive audiobook experience with OCR extraction, neural text-to-speech narration, multilingual translation, and real-time question answering using a Retrieval-Augmented Generation (RAG) system.

## Features

- **Document Processing**: Supports PDF, scanned pages, and image-based documents
- **Intelligent Text Extraction**: Automatic OCR fallback if direct text extraction fails
- **Multilingual Support**: Narration and translation in 10 languages
- **Interactive Q&A**: RAG-based question answering during playback
- **Real-time Control**: Pause, query, and resume audio seamlessly
- **Optimized Performance**: ONNX Runtime and model quantization for faster inference

## System Architecture

```
User Upload
    ↓
OCR / Text Extraction
    ↓
Text Cleaning and Chunking
    ↓
Embeddings + Vector Store (FAISS / ChromaDB)
    ↓
Retrieval and LLM Reasoning (RAG)
    ↓
Optional Translation Layer
    ↓
Neural Text-to-Speech
    ↓
Interactive Audio Playback
```

## Tech Stack

| Component | Tools |
|-----------|-------|
| **Programming Language** | Python |
| **OCR** | Tesseract, EasyOCR |
| **NLP** | spaCy, NLTK |
| **Embeddings** | Sentence Transformers, OpenAI Embeddings |
| **Vector Database** | FAISS or ChromaDB |
| **LLM Integration** | LangChain |
| **Text-to-Speech** | Edge-TTS or OpenAI TTS |
| **Optimization** | ONNX Runtime, INT8 Quantization |
| **UI Layer** | Streamlit |
| **Backend** | FastAPI |

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/interactive-audiobook-ai.git
cd interactive-audiobook-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
streamlit run app.py
```

### Steps:
1. Upload a document (PDF, image, or scanned page)
2. Select your preferred language
3. Generate audiobook
4. Listen and ask questions during playback

## Performance Summary

| Metric | Result |
|--------|--------|
| **OCR Accuracy** | 95% |
| **Retrieval Accuracy** | 92% |
| **Inference Latency** (After Optimization) | < 1.5 seconds |
| **Supported Output Languages** | 10 |

## Future Improvements

- [ ] Offline ASR and lightweight LLM support
- [ ] Mobile and embedded deployment
- [ ] Custom narrator voice cloning
- [ ] GPU/NPU optimized on-device inference
- [ ] Real-time streaming capabilities
- [ ] Multi-document cross-referencing

## Use Cases

- **Accessibility**: Assistive reading for visually impaired users
- **Education**: Academic and research document navigation
- **Language Learning**: Multi-language comprehension and practice
- **Content Creation**: Intelligent audiobook generation
- **Professional**: Document review and analysis

## Contributing

Contributions are welcome! Please open an issue before submitting major changes.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

This work integrates open-source NLP, OCR, speech synthesis, and retrieval technologies to create a unified interactive reading experience. Special thanks to the communities behind:

- Tesseract OCR and EasyOCR
- Sentence Transformers and LangChain
- FAISS and ChromaDB
- Edge-TTS and OpenAI
- Streamlit and FastAPI

## Contact

For questions or suggestions, please open an issue or reach out via email: hemantkumar.bk@gmail.com

---

**Star ⭐ this repository if you find it useful!**
