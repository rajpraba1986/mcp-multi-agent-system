# Browserbase Web Extraction - Configuration Guide

## Overview

The Browserbase web extraction system now supports **configurable extraction types** that can be customized through configuration files. This allows you to define custom extraction behaviors, domain-specific settings, and reusable extraction patterns.

## ✅ Current Status

The configurable extraction system is **WORKING** with the following features:

- ✅ **Extraction Type Configuration**: Define custom extraction types in YAML
- ✅ **Alias Support**: Use alternative names for extraction types (e.g., "full" = "comprehensive")  
- ✅ **Domain Auto-Detection**: Automatic extraction type selection based on URL domain
- ✅ **Fallback Support**: Works even if config loading fails with sensible defaults
- ✅ **Real-Time Configuration**: Changes to extraction behavior through simple parameter updates

## 🎯 Available Extraction Types

### 1. **General Types**

| Type | Aliases | Description | Use Cases |
|------|---------|-------------|-----------|
| `general` | - | Basic content extraction with text, links, minimal metadata | Basic web scraping, content monitoring |
| `comprehensive` | `full`, `complete`, `all` | Extract ALL available data from webpage | Website analysis, SEO auditing, content inventory |

### 2. **Domain-Specific Types**

| Type | Domains | Features | Use Cases |
|------|---------|----------|-----------|
| `financial` | finance.yahoo.com, marketbeat.com, bloomberg.com | Stock prices, market data, analyst ratings | Investment research, market monitoring |
| `competitor_analysis` | marketbeat.com | Competitor tables, comparison metrics | Market analysis, competitive intelligence |
| `github` | github.com | Repository info, languages, user stats | Developer portfolio analysis, tech stack research |
| `news` | news.ycombinator.com, reddit.com | Article headlines, story rankings, discussions | News monitoring, trend analysis |
| `cryptocurrency` | coinmarketcap.com, coingecko.com | Crypto prices, market cap, trading volumes | Crypto portfolio tracking, market analysis |

## 📋 Configuration Files

### Main Configuration: `config/extraction_config.yaml`

This file contains all extraction type definitions, domain mappings, and settings. Key sections:

```yaml
# Default settings applied to all extractions
default_extraction:
  type: "general"
  take_screenshot: true
  timeout: 30000
  wait_for_content: 4000

# Available extraction types and their configurations  
extraction_types:
  comprehensive:
    description: "Extract ALL available data from webpage"
    aliases: ["full", "complete", "all"]
    domains: ["*"]
    features: 
      - "Full text content (no limits)"
      - "All links with metadata"
      - "Complete heading structure (H1-H6)"
      - "All forms with input details"
      - "All tables with headers and data"
    wait_time: 5000

# Domain-specific automatic type selection
domain_configs:
  "finance.yahoo.com":
    extraction_type: "financial"
    wait_time: 6000
    scroll_to_load: true
```

## 🚀 Usage Examples

### 1. **Basic Usage**

```bash
curl -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "extract_website_data",
      "arguments": {
        "url": "https://example.com",
        "extraction_type": "general"
      }
    }
  }'
```

### 2. **Comprehensive Extraction (All Data)**

```bash
# Any of these aliases work for comprehensive extraction:
"extraction_type": "comprehensive"
"extraction_type": "full" 
"extraction_type": "complete"
"extraction_type": "all"
```

**Result**: Full structured data with headings, images, forms, tables, meta tags, and content statistics.

### 3. **Domain-Specific Extraction**

```bash
# Hacker News - automatically detected as "news" type
{
  "url": "https://news.ycombinator.com",
  "extraction_type": "general"  # Will auto-upgrade to "news"
}

# Result: Structured data with top_stories array containing:
# - Story titles and URLs
# - Points and rankings  
# - Publication metadata
```

### 4. **Financial Data Extraction**

```bash
{
  "url": "https://finance.yahoo.com/quote/AAPL",
  "extraction_type": "financial"  # Or auto-detected
}

# Result: Stock prices, market data, financial metrics
```

## 🔧 Configuration Customization

### Adding New Extraction Types

1. **Edit `config/extraction_config.yaml`**:

```yaml
extraction_types:
  my_custom_type:
    description: "Custom extraction for my specific needs"
    aliases: ["custom", "mine"]
    domains: ["mysite.com"]
    features:
      - "Custom feature 1"  
      - "Custom feature 2"
    wait_time: 3000
```

2. **Add Domain Mapping**:

```yaml
domain_configs:
  "mysite.com":
    extraction_type: "my_custom_type"
    wait_time: 3000
    scroll_to_load: true
```

3. **Use Your Custom Type**:

```bash
{
  "url": "https://mysite.com/page",
  "extraction_type": "custom"  # Uses your custom type
}
```

### Modifying Extraction Settings

```yaml
extraction_settings:
  # Screenshot configuration
  screenshots:
    enabled: true
    full_page: true
    directory: "data/screenshots"
    format: "png"
    
  # Content limits per extraction type
  content_limits:
    general:
      max_content_length: 2000
      max_links: 20
    comprehensive:
      max_content_length: null  # No limit
      max_links: null          # No limit
      
  # Timeout and reliability settings
  reliability:
    max_retries: 3
    retry_delay: 2000
    page_load_timeout: 30000
```

## 🔄 Configuration Priority

The system resolves extraction types in this order:

1. **Explicit Parameter**: `extraction_type` passed in request
2. **Domain-Specific Config**: Automatic detection based on URL domain
3. **Default Configuration**: From `default_extraction` in config file
4. **System Default**: "general" if all else fails

## ⚡ Real-World Examples

### Example 1: Market Analysis Pipeline

```bash
# Get comprehensive competitor data
curl -X POST http://localhost:8001/mcp \
  -d '{
    "params": {
      "name": "extract_website_data", 
      "arguments": {
        "url": "https://www.marketbeat.com/stocks/NYSE/AAPL/competitors/",
        "extraction_type": "comprehensive"  # Get ALL data
      }
    }
  }'

# Result: Complete competitor tables, financial metrics, analysis data
```

### Example 2: Tech News Monitoring

```bash
# Monitor Hacker News trends
curl -X POST http://localhost:8001/mcp \
  -d '{
    "params": {
      "name": "extract_website_data",
      "arguments": {
        "url": "https://news.ycombinator.com",
        "extraction_type": "news"  # Or auto-detected
      }
    }
  }'

# Result: Structured top_stories with titles, points, rankings
```

### Example 3: Developer Portfolio Analysis

```bash
# Analyze GitHub profile
curl -X POST http://localhost:8001/mcp \
  -d '{
    "params": {
      "name": "extract_website_data",
      "arguments": {
        "url": "https://github.com/torvalds",
        "extraction_type": "github"  # Or auto-detected
      }
    }
  }'

# Result: Repository info, languages, user statistics
```

## 🏗️ Architecture Benefits

1. **Flexibility**: Add new extraction types without code changes
2. **Maintainability**: Centralized configuration management
3. **Extensibility**: Easy to add domain-specific extraction logic
4. **Fallback Support**: Graceful degradation if config fails
5. **Alias System**: User-friendly alternative names for extraction types
6. **Auto-Detection**: Smart domain-based type selection

## 📈 Performance Features

- **Configurable Timeouts**: Per-type timeout settings
- **Domain-Specific Wait Times**: Optimized for different site loading patterns  
- **Content Limits**: Configurable limits to prevent oversized extractions
- **Screenshot Control**: Enable/disable per extraction type
- **Retry Logic**: Configurable retry attempts and delays

## 🔍 Debugging

Check server logs for configuration resolution:

```
[INFO] Using extraction type: 'comprehensive' (requested: 'full')
[INFO] 🔥 Using COMPREHENSIVE extraction mode - extracting ALL data
```

The logs show:
- Requested type vs resolved type
- Alias resolution (e.g., 'full' → 'comprehensive')  
- Domain-specific detection
- Extraction mode selection

## ✨ Next Steps

1. **Customize**: Edit `config/extraction_config.yaml` for your needs
2. **Extend**: Add your own extraction types and domain mappings
3. **Monitor**: Check logs for extraction type resolution
4. **Optimize**: Adjust timeouts and limits for your use cases

The configurable extraction system makes the Browserbase agent highly flexible and customizable for any web extraction workflow! 🎉
