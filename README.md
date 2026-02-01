# Memos MCP Server

[![uvx](https://img.shields.io/badge/uvx-ready-blue)](https://github.com/astral-sh/uvx)

A Model Context Protocol (MCP) server that provides integration with [usememos](https://github.com/usememos/memos), allowing AI assistants to interact with your Memos instance for managing notes, memos, and knowledge bases.

## Features

### Tools
- **create_memo**: Create new memos with content and visibility settings
- **list_memos**: List memos with optional filtering (page, visibility, tags)
- **get_memo**: Retrieve specific memo by ID
- **update_memo**: Update existing memo content, visibility, or status
- **delete_memo**: Delete memos
- **search_memos**: Search memos by content
- **get_tags**: Get all available tags

### Resources
- **memo://{id}**: Access individual memo content
- **memos://list**: Access list of recent memos
- **memos://search/{query}**: Access search results

### Prompts
- **memo_summary**: Generate summaries of recent memos
- **memo_organization**: Help organize and analyze memos

## Installation

### Option 1: Direct Installation with uvx (Recommended)

```bash
uvx --from git+https://github.com/bigcat26/memos-mcp.git memos-mcp
```

### Option 2: Manual Installation for Development

```bash
git clone https://github.com/bigcat26/memos-mcp.git
cd memos-mcp
pip install -r requirements.txt
```

---

## 🌐 Repository

- **GitHub**: https://github.com/bigcat26/memos-mcp
- **usememos**: https://github.com/usememos/memos
   
2. Or clone for local development:
   ```bash
   git clone https://github.com/bigcat26/memos-mcp.git
   cd memos-mcp
   pip install -r requirements.txt
   ```

## Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file with your Memos configuration:
   ```env
   # Required: Your Memos instance URL
   MEMOS_BASE_URL=https://your-memos-instance.com
   
   # Required: Access token from Memos settings
   MEMOS_ACCESS_TOKEN=your_access_token_here
   
   # Optional settings
   MEMOS_API_PREFIX=/api/v1
   MEMOS_TIMEOUT=30
   LOG_LEVEL=INFO
   ```

### Getting Access Token

1. Log into your Memos instance
2. Go to **Settings** > **My Account**
3. Click **Create Access Token**
4. Give it a descriptive name
5. Copy the generated token to your `.env` file

## Usage

### Running the Server (Recommended)

```bash
# Install and run with uvx
uvx --from git+https://github.com/bigcat26/memos-mcp.git memos-mcp
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Direct execution
python -m memos_mcp.server
```

### Integration with AI Assistants

Add this server to your AI assistant's MCP configuration:

```json
{
  "mcpServers": {
    "memos": {
      "command": "uvx",
      "args": ["run", "bigcat26/memos-mcp"],
      "env": {
        "MEMOS_BASE_URL": "https://your-memos-instance.com",
        "MEMOS_ACCESS_TOKEN": "your_access_token_here"
      }
    }
  }
}
```

## Example Usage

Once connected to your AI assistant, you can:

```
Create a new memo:
"Create a memo about my project deadline next week"

List recent memos:
"Show me my latest 10 memos"

Search memos:
"Search for memos containing 'meeting'"

Get a specific memo:
"Get memo #123"

Update a memo:
"Update memo #123 to add more details"

Delete a memo:
"Delete memo #456"

Access memo as resource:
"Read memo://123 for me"

Generate summary:
"Create a summary of my recent memos"

Help organize:
"Help me organize my memos about projects"
```

## API Endpoints Used

This MCP server integrates with the following Memos API endpoints:

- `POST /api/v1/memos` - Create memo
- `GET /api/v1/memos` - List/search memos
- `GET /api/v1/memo/{id}` - Get specific memo
- `PATCH /api/v1/memo/{id}` - Update memo
- `DELETE /api/v1/memo/{id}` - Delete memo
- `GET /api/v1/tags` - Get tags
- `GET /api/v1/user/me` - Get user info

## Error Handling

The server includes comprehensive error handling:

- **Connection errors**: Reports connectivity issues
- **Authentication errors**: Invalid or missing access tokens
- **API errors**: Proper error messages from Memos API
- **Validation errors**: Invalid input parameters
- **Network timeouts**: Configurable timeout settings

## Logging

Configure logging level with the `LOG_LEVEL` environment variable:
- `DEBUG`: Detailed debugging information
- `INFO`: General information (default)
- `WARNING`: Warning messages
- `ERROR`: Error messages only

## Development

### Project Structure

```
memos-mcp/
├── memos_mcp/
│   ├── __init__.py
│   ├── server.py           # Main MCP server implementation
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py       # Configuration management
│   │   └── client.py       # Memos API client
│   ├── tools/              # Tool implementations
│   ├── resources/          # Resource implementations
│   └── prompts/            # Prompt templates
├── requirements.txt
├── .env.example
├── package.json
└── README.md
```

### Testing

To test the server:

```bash
# Test configuration
python -c "from memos_mcp.utils.config import settings; settings.validate_config(); print('Configuration OK')"

# Test API connection
python -c "from memos_mcp.utils.client import memos_client; print(memos_client.get_user_info())"
```

## Troubleshooting

### Common Issues

1. **Connection refused**: Check MEMOS_BASE_URL is correct and accessible
2. **Authentication failed**: Verify MEMOS_ACCESS_TOKEN is valid and not expired
3. **SSL errors**: Ensure your Memos instance uses a valid SSL certificate
4. **Timeout errors**: Increase MEMOS_TIMEOUT if needed

### Debug Mode

Enable debug logging:

```env
LOG_LEVEL=DEBUG
```

This will show detailed HTTP requests and responses.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

Apache 2.0 License - see LICENSE file for details.

## Support

For issues:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Verify your configuration
4. Test API connectivity directly
