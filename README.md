<a href="https://x.com/alxfazio" target="_blank">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="images/firecrawl-mcp-examples-github-banner.png">
    <img alt="Firecrawl Quickstarts Logo" src="images/firecrawl-mcp-examples-github-banner.png" width="400px" style="max-width: 100%; margin-bottom: 20px;">
  </picture>
</a>

# Firecrawl MCP Examples

A collection of Model Context Protocol (MCP) servers that provide tools for Claude and other LLMs to interact with various data sources using Firecrawl API.

## Examples

### Hacker News MCP Server

A server that provides tools for:

1. Accessing Hacker News content and discussions
2. Scraping websites using the Firecrawl API
3. Searching for Hacker News discussions on any topic

Features:
- `get_hnews_item`: Get details about a specific Hacker News post or comment
- `get_hnews_popular_discussions`: Get the top 30 discussions on Hacker News
- `firecrawl_scrape_url`: Extract clean, readable content from any URL
- `search_hnews`: Search for Hacker News discussions about a specific topic

## Setup

### Requirements

- Python 3.10+
- [UV package manager](https://github.com/astral-sh/uv)
- Firecrawl API key (stored in `.env` file)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv install -e .
   ```
3. Create a `.env` file with your Firecrawl API key:
   ```
   FIRECRAWL_API_KEY=your-api-key-here
   ```

### Usage with Claude Desktop

1. Configure Claude Desktop to use this MCP server (see Claude Desktop documentation)
2. Start the server:
   ```bash
   uv run server.py
   ```
3. In Claude Desktop, you'll have access to Hacker News tools and web scraping capabilities

## License

MIT License