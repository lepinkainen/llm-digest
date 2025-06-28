# Enhanced URL Summarizer

A comprehensive command-line tool that automatically summarizes URLs using appropriate LLM fragments. This enhanced version combines the best features from multiple implementations to provide a robust, user-friendly experience.

## ✨ Features

### 🔍 **Smart URL Detection**

- Automatic detection of URL types (Reddit, Hacker News, YouTube)
- Multiple extraction methods for robust ID parsing
- Fallback mechanisms for edge cases
- Support for various URL formats and subdomains

### 🎯 **Flexible Output Formats**

- **Bullet points** (default): Concise 3-5 bullet summary
- **Paragraph**: Single paragraph overview
- **Detailed**: Comprehensive analysis with context

### 🛠️ **Advanced Configuration**

- Configurable LLM models (GPT-4, GPT-3.5-turbo, etc.)
- Custom system prompts
- Adjustable timeouts
- Debug mode for troubleshooting

### 🖥️ **Multiple Usage Modes**

- **Interactive CLI**: Continuous processing of multiple URLs
- **Single command**: Process one URL and exit
- **Batch processing**: Handle multiple URLs efficiently

### 🛡️ **Comprehensive Error Handling**

- Detailed validation and error messages
- Installation guidance for missing dependencies
- Network timeout handling
- Graceful failure recovery

### 📦 **Professional Development**

- Modern Python packaging with `uv`
- Comprehensive test suite
- Type hints and documentation
- Code formatting and linting

## 🎯 Supported Sites

| Site            | Fragment                | Supported URLs                 |
| --------------- | ----------------------- | ------------------------------ |
| **Reddit**      | `llm-fragments-reddit`  | `reddit.com`, `www.reddit.com` |
| **Hacker News** | `llm-hacker-news`       | `news.ycombinator.com`         |
| **YouTube**     | `llm-fragments-youtube` | `youtube.com`, `youtu.be`      |

## 🚀 Installation

### Using uv (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd enhanced-url-summarizer

# Install with uv (installs all dependencies)
uv sync

# Or install in development mode
uv sync --group dev

# Add to your PATH (optional)
uv tool install .
```

### Manual Installation

```bash
# Install core dependencies
uv add llm llm-fragments-reddit llm-hacker-news llm-fragments-youtube

# Install the package
uv pip install -e .
```

### Verify Installation

```bash
# Check if llm is working
llm --version

# Configure your LLM provider (required)
llm keys set openai  # or your preferred provider
```

## 📖 Usage

### Interactive Mode

Start the interactive CLI for processing multiple URLs:

```bash
url-summarizer
```

**Example session:**

```
🔗 Enhanced URL Summarizer v1.0.0
==================================================
Supported sites:
  • reddit.com (llm-fragments-reddit)
```
