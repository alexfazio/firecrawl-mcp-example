import os
import json
from typing import Optional, Dict, Any, List, Union
import httpx
from datetime import datetime
import time
import asyncio
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# ==================== SERVER INITIALIZATION START ====================
# Load environment variables from .env file
load_dotenv()

# Get the Firecrawl API key from environment variables
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

# Initialize the FastMCP server with a unique name
mcp = FastMCP("hn-firecrawl-service")

# Base URL for the Hacker News API
HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
# ==================== SERVER INITIALIZATION END ====================

# ==================== HELPER FUNCTIONS START ====================

# ==================== API CORE HELPERS ====================

async def make_hn_request(endpoint: str) -> Optional[Union[Dict[str, Any], List[int], int]]:
    """Make a request to the Hacker News API with proper error handling.
    
    Args:
        endpoint: The API endpoint to query (without the base URL)
    
    Returns:
        The JSON response data, or None if the request failed
    """
    url = f"{HN_API_BASE}/{endpoint}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError:
            return None
        except httpx.HTTPStatusError:
            return None
        except Exception:
            return None

async def get_item(item_id: int) -> Optional[Dict[str, Any]]:
    """Fetch an item from the Hacker News API by its ID.
    
    Args:
        item_id: The ID of the item to fetch
    
    Returns:
        The item data, or None if not found
    """
    result = await make_hn_request(f"item/{item_id}.json")
    if isinstance(result, dict):
        return result
    return None

# ==================== FIRECRAWL HELPERS ====================

async def firecrawl_scrape_md(url: str) -> str:
    """Scrape a URL and return the content in Markdown format using Firecrawl.
    
    Args:
        url: The URL to scrape
    """
    if not FIRECRAWL_API_KEY:
        return "Error: Firecrawl API key not found in environment variables"
    
    # Using the correct endpoint from the API spec
    firecrawl_url = "https://api.firecrawl.dev/v1/scrape"
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Using the correct payload structure from the API spec
    payload = {
        "url": url,
        "formats": ["markdown"]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                firecrawl_url, 
                headers=headers, 
                json=payload, 
                timeout=60.0
            )
            response.raise_for_status()
            
            result = response.json()
            
            # According to the API spec, the response structure is:
            # { "success": true, "data": { "markdown": "..." } }
            if result.get("success") and "data" in result and "markdown" in result["data"]:
                return result["data"]["markdown"]
            else:
                return f"Error scraping {url}: No markdown content returned. Response: {json.dumps(result)}"
    
    except httpx.HTTPStatusError as e:
        return f"HTTP error while scraping {url}: {str(e)}"
    except httpx.RequestError as e:
        return f"Request error while scraping {url}: {str(e)}"
    except Exception as e:
        return f"Unexpected error while scraping {url}: {str(e)}"

# ==================== HACKER NEWS HELPERS ====================

async def hnews_get_post_title(post_data: Dict[str, Any]) -> str:
    """Extract the title from a Hacker News post."""
    return post_data.get("title", "No title available")

async def hnews_get_post_id(post_data: Dict[str, Any]) -> int:
    """Extract the ID from a Hacker News post."""
    return post_data.get("id", 0)

async def hnews_get_post_author(post_data: Dict[str, Any]) -> str:
    """Extract the author from a Hacker News post."""
    return post_data.get("by", "Anonymous")

async def hnews_get_post_score(post_data: Dict[str, Any]) -> int:
    """Extract the score from a Hacker News post."""
    return post_data.get("score", 0)

async def hnews_get_post_time(post_data: Dict[str, Any]) -> str:
    """Extract the time from a Hacker News post and format it as a relative time."""
    timestamp = post_data.get("time", 0)
    current_time = int(time.time())
    diff = current_time - timestamp
    
    if diff < 60:
        return "just now"
    elif diff < 3600:
        minutes = diff // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif diff < 86400:
        hours = diff // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    else:
        days = diff // 86400
        return f"{days} day{'s' if days > 1 else ''} ago"

async def hnews_get_post_time_absolute(post_data: Dict[str, Any]) -> str:
    """Extract the time from a Hacker News post and format it as an absolute time."""
    timestamp = post_data.get("time", 0)
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

async def hnews_get_post_type(post_data: Dict[str, Any]) -> str:
    """Extract the type from a Hacker News post."""
    return post_data.get("type", "unknown")

async def hnews_get_post_content_text(post_data: Dict[str, Any]) -> str:
    """Extract the text content from a Hacker News post."""
    return post_data.get("text", "No text content available")

async def hnews_get_post_discussion_url(post_data: Dict[str, Any]) -> str:
    """Generate the discussion URL for a Hacker News post."""
    post_id = post_data.get("id", 0)
    return f"https://news.ycombinator.com/item?id={post_id}"

async def hnews_get_post_external_article_url(post_data: Dict[str, Any]) -> str:
    """Extract the external article URL from a Hacker News post."""
    return post_data.get("url", "No external URL available")

async def hnews_get_post_comment_count(post_data: Dict[str, Any]) -> int:
    """Extract the comment count from a Hacker News post."""
    # Use descendants if available (total count including nested comments)
    # Fall back to kids length (only direct comments)
    return post_data.get("descendants", len(post_data.get("kids", [])))

async def hnews_get_post_metadata(post_data: Dict[str, Any]) -> str:
    """Format comprehensive metadata about a Hacker News post."""
    title = await hnews_get_post_title(post_data)
    author = await hnews_get_post_author(post_data)
    score = await hnews_get_post_score(post_data)
    time = await hnews_get_post_time_absolute(post_data)
    comment_count = await hnews_get_post_comment_count(post_data)
    
    return f"Title: {title}\nAuthor: {author}\nScore: {score}\nTime: {time}\nComments: {comment_count}"

# ==================== HACKER NEWS TOPLIST HELPERS ====================

async def hnews_get_toplist_articles() -> List[int]:
    """Fetch the current top stories from Hacker News."""
    result = await make_hn_request("topstories.json")
    if isinstance(result, list):
        return result[:30]  # Return top 30 stories for efficiency
    return []

async def hnews_get_toplist_article_id(toplist_item: Dict[str, Any]) -> int:
    """Extract the ID from a toplist article."""
    return toplist_item.get("id", 0)

async def hnews_get_toplist_article_title(toplist_item: Dict[str, Any]) -> str:
    """Extract the title from a toplist article."""
    return toplist_item.get("title", "No title available")

async def hnews_get_toplist_article_rank(toplist_item: Dict[str, Any], index: int) -> int:
    """Get the rank of an article in the toplist."""
    return index + 1

async def hnews_get_toplist_article_score(toplist_item: Dict[str, Any]) -> int:
    """Extract the score from a toplist article."""
    return toplist_item.get("score", 0)

async def hnews_get_toplist_article_author(toplist_item: Dict[str, Any]) -> str:
    """Extract the author from a toplist article."""
    return toplist_item.get("by", "Anonymous")

async def hnews_get_toplist_article_age(toplist_item: Dict[str, Any]) -> str:
    """Calculate the age of a toplist article."""
    # Reuse the post time function which gives a relative time
    return await hnews_get_post_time(toplist_item)

async def hnews_get_toplist_article_type(toplist_item: Dict[str, Any]) -> str:
    """Extract the type from a toplist article."""
    return toplist_item.get("type", "unknown")

async def hnews_get_toplist_external_article_url(toplist_item: Dict[str, Any]) -> str:
    """Extract the external article URL from a toplist article."""
    return toplist_item.get("url", "No external URL available")

async def hnews_get_toplist_discussion_url(toplist_item: Dict[str, Any]) -> str:
    """Generate the discussion URL for a toplist article."""
    post_id = toplist_item.get("id", 0)
    return f"https://news.ycombinator.com/item?id={post_id}"

async def hnews_get_toplist_comment_count(toplist_item: Dict[str, Any]) -> int:
    """Extract the comment count from a toplist article."""
    return len(toplist_item.get("kids", []))

# ==================== GOOGLE SEARCH HELPERS ====================

async def search_google_for_hnews(query: str) -> List[Dict[str, str]]:
    """Helper function to search Google for Hacker News content.

    Args:
        query: The search query
    """
    # Format the query for a Google search limited to Hacker News
    formatted_query = query.replace(" ", "+")
    search_url = f"https://www.google.com/search?q=site:news.ycombinator.com+{formatted_query}"
    
    # Use Firecrawl to get the search results page
    markdown_content = await firecrawl_scrape_md(search_url)
    
    # Check if there's an error message from Firecrawl
    if markdown_content.startswith("Error:") or markdown_content.startswith("HTTP error"):
        print(f"Firecrawl error: {markdown_content}")
        return []
    
    # Parse the results using a more robust approach
    results = []
    
    # Split content into lines for processing
    lines = markdown_content.split("\n")
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for links which are formatted as [text](url) in markdown
        if "news.ycombinator.com" in line and ("[" in line or "http" in line):
            result = {}
            
            # Extract URL - handle both markdown links [text](url) and plain URLs
            if "(" in line and ")" in line and "[" in line and "]" in line:
                # Markdown format: [title](url)
                url_start = line.find("(") + 1
                url_end = line.find(")", url_start)
                if url_start > 0 and url_end > url_start:
                    url = line[url_start:url_end].strip()
                    if "news.ycombinator.com" in url:
                        result["url"] = url
                        
                        # Extract title from markdown link
                        title_start = line.find("[") + 1
                        title_end = line.find("]", title_start)
                        if title_start > 0 and title_end > title_start:
                            result["title"] = line[title_start:title_end].strip()
            else:
                # Try to find a plain URL
                words = line.split()
                for word in words:
                    if word.startswith("http") and "news.ycombinator.com" in word:
                        result["url"] = word.strip()
                        break
            
            # If we have a URL but no title, look in surrounding lines for title
            if result.get("url") and not result.get("title"):
                # Look at current line first
                potential_title = line.strip()
                if "http" in potential_title:
                    # Remove the URL part for cleaner title
                    url_index = potential_title.find("http")
                    if url_index > 0:
                        potential_title = potential_title[:url_index].strip()
                
                # If current line doesn't have a good title, check previous and next lines
                if not potential_title or len(potential_title) < 5:
                    if i > 0:
                        prev_line = lines[i-1].strip()
                        if prev_line and "http" not in prev_line and len(prev_line) > 5:
                            potential_title = prev_line
                    if (not potential_title or len(potential_title) < 5) and i < len(lines)-1:
                        next_line = lines[i+1].strip()
                        if next_line and "http" not in next_line and len(next_line) > 5:
                            potential_title = next_line
                
                if potential_title and len(potential_title) > 5:
                    result["title"] = potential_title
            
            # If we still don't have a title, use a placeholder
            if result.get("url") and not result.get("title"):
                result["title"] = "Hacker News Discussion"
            
            # Look for description in next few lines
            description_lines = []
            j = i + 1
            while j < min(i + 5, len(lines)) and not result.get("description"):
                next_line = lines[j].strip()
                # Skip empty lines or lines that look like URLs
                if next_line and "http" not in next_line and not next_line.startswith("..."):
                    description_lines.append(next_line)
                j += 1
            
            if description_lines:
                result["description"] = " ".join(description_lines)
            else:
                result["description"] = "No description available"
            
            # Add to results if we have the minimum required data
            if result.get("url") and result.get("title"):
                # Clean up the URL if needed (remove trailing punctuation)
                if result["url"][-1] in '.,:;)]}':
                    result["url"] = result["url"][:-1]
                
                # Make sure it's a complete URL
                if not result["url"].startswith("http"):
                    result["url"] = "https://" + result["url"]
                
                results.append(result)
        
        i += 1
    
    # If we couldn't find structured results, try to extract any HN URLs as a fallback
    if not results:
        for line in lines:
            if "news.ycombinator.com/item?id=" in line:
                # Find the URL
                start_idx = line.find("news.ycombinator.com")
                if start_idx > 0:
                    # Look for the start of the URL
                    url_start = line.rfind("http", 0, start_idx)
                    if url_start == -1:  # No http found, try with www
                        url_start = line.rfind("www", 0, start_idx)
                    if url_start == -1:  # Still not found, just use the domain
                        url_start = start_idx
                        url = "https://" + line[url_start:]
                    else:
                        url = line[url_start:]
                    
                    # Find the end of the URL
                    url_end = len(url)
                    for char in [' ', ')', ']', '"', "'"]:
                        pos = url.find(char)
                        if pos != -1 and pos < url_end:
                            url_end = pos
                    
                    url = url[:url_end]
                    
                    results.append({
                        "url": url,
                        "title": "Hacker News Discussion",
                        "description": "Found through Google search"
                    })
    
    return results

# ==================== HELPER FUNCTIONS END ====================

# ==================== MCP TOOLS START ====================
@mcp.tool()
async def get_hnews_item(item_id: int) -> str:
    """Retrieve detailed information about a specific Hacker News item.
    
    This tool fetches comprehensive details about a Hacker News post or comment
    by its ID, including metadata, content, and relevant URLs.

    Args:
        item_id: The numeric identifier of the Hacker News item (e.g., 34159862)
    """
    # Fetch the item data from Hacker News API
    item_data = await get_item(item_id)
    
    if not item_data:
        return f"Could not find Hacker News item with ID {item_id}"
    
    # Extract item properties using helper functions
    title = await hnews_get_post_title(item_data)
    author = await hnews_get_post_author(item_data)
    score = await hnews_get_post_score(item_data)
    post_time = await hnews_get_post_time_absolute(item_data)
    relative_time = await hnews_get_post_time(item_data)
    item_type = await hnews_get_post_type(item_data)
    comment_count = await hnews_get_post_comment_count(item_data)
    content = await hnews_get_post_content_text(item_data)
    
    # Get URLs
    article_url = await hnews_get_post_external_article_url(item_data)
    discussion_url = await hnews_get_post_discussion_url(item_data)
    
    # Format response in a structured way
    response = f"# {title}\n\n"
    response += f"**Type:** {item_type}\n"
    response += f"**Author:** {author}\n"
    response += f"**Posted:** {post_time} ({relative_time})\n"
    
    if score > 0:
        response += f"**Score:** {score} points\n"
    
    if comment_count > 0:
        response += f"**Comments:** {comment_count}\n"
    
    response += "\n**Links:**\n"
    response += f"- Discussion: {discussion_url}\n"
    
    if article_url != "No external URL available":
        response += f"- Article: {article_url}\n"
    
    if content != "No text content available":
        response += f"\n**Content:**\n{content}\n"
    
    # Add children info if available
    if "kids" in item_data and item_data["kids"]:
        response += f"\n**Has {len(item_data['kids'])} direct replies**\n"
    
    return response

@mcp.tool()
async def get_hnews_popular_discussions() -> str:
    """Retrieve today's top discussions on Hacker News.
    
    This tool fetches the current top 30 stories from Hacker News,
    sorted by score. For each story, it provides the title, author,
    score, comment count, post time, and relevant URLs.
    """
    # Get the top stories IDs
    top_ids = await hnews_get_toplist_articles()
    
    if not top_ids:
        return "Could not fetch popular discussions from Hacker News"
    
    # Limit to top 30 as specified
    top_ids = top_ids[:30]
    
    # Fetch details for each story
    discussions = []
    for i, story_id in enumerate(top_ids):
        story_data = await get_item(story_id)
        if story_data:
            # Use helper functions to extract all required information
            rank = i + 1
            title = await hnews_get_toplist_article_title(story_data)
            score = await hnews_get_toplist_article_score(story_data)
            author = await hnews_get_toplist_article_author(story_data)
            age = await hnews_get_toplist_article_age(story_data)
            post_type = await hnews_get_toplist_article_type(story_data)
            comments = await hnews_get_toplist_comment_count(story_data)
            
            # Get URLs
            discussion_url = await hnews_get_toplist_discussion_url(story_data)
            article_url = await hnews_get_toplist_external_article_url(story_data)
            
            # Get content as a summary
            content = await hnews_get_post_content_text(story_data)
            if content != "No text content available":
                # Limit content to a reasonable summary length
                if len(content) > 200:
                    content = content[:197] + "..."
                summary = f"\n   Summary: {content}"
            else:
                summary = ""
            
            # Format each discussion with all required information
            discussion_info = f"#{rank}: {title}\n"
            discussion_info += f"   Type: {post_type} | Score: {score} points | By: {author} | Posted: {age}\n"
            discussion_info += f"   Comments: {comments}\n"
            
            # Add URLs
            discussion_info += f"   Discussion: {discussion_url}\n"
            if article_url != "No external URL available":
                discussion_info += f"   Article: {article_url}"
            
            # Add summary if available
            discussion_info += summary
            
            discussions.append(discussion_info)
    
    if not discussions:
        return "No discussions found"
    
    return "# TOP 30 HACKER NEWS DISCUSSIONS\n\n" + "\n\n".join(discussions)

@mcp.tool()
async def firecrawl_scrape_url(url: str) -> str:
    """Extract clean, readable content from any web page.

    This tool scrapes the specified URL and returns the content in a clean,
    readable Markdown format. It handles JavaScript-rendered sites and complex
    layouts, extracting just the main content.

    Args:
        url: The complete web address to scrape (e.g., "https://example.com/page")
    """
    markdown_content = await firecrawl_scrape_md(url)
    
    # Check if there was an error in scraping
    if markdown_content.startswith("Error:") or markdown_content.startswith("HTTP error"):
        return f"Failed to scrape {url}: {markdown_content}"
    
    # Limit the response length if needed
    if len(markdown_content) > 8000:
        markdown_content = markdown_content[:8000] + "...\n\n[Content truncated due to length]"
    
    return f"# Content from {url}\n\n{markdown_content}"

@mcp.tool()
async def search_hnews(query: str) -> str:
    """Search for Hacker News discussions matching specific keywords.
    
    This tool performs a targeted search for Hacker News content using Google
    and returns relevant discussions with their titles, URLs, and brief descriptions.
    Results are sorted by relevance to your query.

    Args:
        query: The search terms to find in Hacker News discussions (e.g., "Python web frameworks", "startup funding")
    """
    if not query.strip():
        return "Error: Search query cannot be empty."
    
    # Search for HN content via Google
    search_results = await search_google_for_hnews(query)
    
    # Format the results
    if not search_results:
        return f"No Hacker News discussions found for query: '{query}'"
    
    formatted_results = []
    for i, result in enumerate(search_results[:10]):  # Limit to top 10 results
        title = result.get("title", "Untitled Discussion")
        url = result.get("url", "")
        description = result.get("description", "No description available")
        
        # Format each result with clear structure and markdown
        formatted_results.append(
            f"### {i+1}. {title}\n"
            f"**Link**: [{url}]({url})\n"
            f"**Description**: {description}\n"
        )
    
    header = f"# SEARCH RESULTS FOR '{query}' ON HACKER NEWS\n\n"
    footer = "\n\n*Results retrieved via Google site-specific search*"
    
    return header + "\n".join(formatted_results) + footer

# ==================== MCP TOOLS END ====================

# ==================== SERVER EXECUTION START ====================
if __name__ == "__main__":
    # Initialize and run the server with stdio transport
    mcp.run(transport='stdio')
# ==================== SERVER EXECUTION END ====================