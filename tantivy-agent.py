#!/usr/bin/env python3
"""
Universal Tantivy Agent - All-in-one document indexing and search solution

This script provides complete functionality for document indexing and search
using Tantivy with flexible JSON configuration.

Usage:
    python tantivy-agent.py <command> [options]

Commands:
    index      - Create or update document index
    search     - Search in indexed documents
    clear      - Clear the index
    install    - Install Claude hooks and setup
    hook-clear - Clear index (used by Claude hooks)
"""

import os
import sys
import json
import yaml
import re
import shutil
import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path
import tantivy


class TantivyAgent:
    """Main Tantivy Agent class with all functionality"""

    def __init__(self, config_path=None):
        """Initialize agent with configuration"""
        self.project_root = self._find_project_root()
        self.config_path = config_path or os.path.join(self.project_root, '.tantivi2agents.json')
        self.config = self._load_config()

    def _find_project_root(self):
        """Find project root by looking for .git directory"""
        current = os.getcwd()
        while current != '/':
            if os.path.exists(os.path.join(current, '.git')):
                return current
            current = os.path.dirname(current)
        return os.getcwd()

    def _load_config(self):
        """Load configuration from JSON file with defaults"""
        default_config = {
            "version": "1.0",
            "index_dir": ".tantivy-data",
            "global_patterns": {
                "include": ["*.md", "*.txt"],
                "exclude": ["*.tmp", "*~", "*.bak"]
            },
            "index_dirs": ["docs/", "guides/", "servers/", "incidents/"],
            "schema_fields": {
                "title": {"weight": 2.0, "tokenizer": "en_stem"},
                "body": {"weight": 1.0, "tokenizer": "en_stem"},
                "tags": {"weight": 1.5, "tokenizer": "default"},
                "servers": {"weight": 1.5, "tokenizer": "default"},
                "path": {"weight": 0.5, "tokenizer": "raw"}
            },
            "search": {
                "default_limit": 10,
                "hide_incidents": True
            },
            "auto_hook": True
        }

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                # Merge with defaults
                config = {**default_config, **user_config}
                return config
            except Exception as e:
                print(f"Error loading config: {e}")
                print("Using default configuration.")

        return default_config

    def _ensure_data_dir(self):
        """Ensure data directory exists and is in .gitignore"""
        data_dir = os.path.join(self.project_root, self.config['index_dir'])
        os.makedirs(data_dir, exist_ok=True)

        # Add to .gitignore if not present
        gitignore_path = os.path.join(self.project_root, '.gitignore')
        gitignore_entry = f"{self.config['index_dir']}/"

        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                gitignore_content = f.read()

            if gitignore_entry not in gitignore_content.splitlines():
                with open(gitignore_path, 'a', encoding='utf-8') as f:
                    f.write(f"\n# Tantivy Agent data\n{gitignore_entry}\n")
        else:
            with open(gitignore_path, 'w', encoding='utf-8') as f:
                f.write(f"# Tantivy Agent data\n{gitignore_entry}\n")

        return data_dir

    def _get_files_for_indexing(self):
        """Get list of files to index based on configuration"""
        files = []

        for dir_config in self.config['index_dirs']:
            if isinstance(dir_config, str):
                dir_path = dir_config
                include_patterns = self.config['global_patterns']['include']
                exclude_patterns = self.config['global_patterns']['exclude']
            else:
                dir_path = dir_config['path']
                include_patterns = dir_config.get('include', self.config['global_patterns']['include'])
                exclude_patterns = dir_config.get('exclude', self.config['global_patterns']['exclude'])

            full_dir_path = os.path.join(self.project_root, dir_path)
            if not os.path.exists(full_dir_path):
                continue

            for root, dirs, filenames in os.walk(full_dir_path):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, self.project_root)

                    # Check include patterns
                    included = any(self._match_pattern(rel_path, pattern) for pattern in include_patterns)

                    # Check exclude patterns
                    excluded = any(self._match_pattern(rel_path, pattern) for pattern in exclude_patterns)

                    if included and not excluded:
                        files.append(file_path)

        return files

    def _match_pattern(self, path, pattern):
        """Simple glob pattern matching"""
        import fnmatch
        return fnmatch.fnmatch(path, pattern)

    def _parse_markdown(self, file_path):
        """Parse markdown file and extract metadata"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None

        meta = {}
        body = content

        # Extract YAML frontmatter
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.S)
        if m:
            header, body = m.groups()
            try:
                meta = yaml.safe_load(header) or {}
            except:
                pass

        # Auto-generate metadata for server files
        rel_path = os.path.relpath(file_path, self.project_root)
        if not meta and rel_path.startswith("servers/"):
            server_name = os.path.splitext(os.path.basename(file_path))[0]
            servers = [server_name]

            # Add base name for numbered servers (mp1 -> mp, ferda7 -> ferda)
            if re.search(r'\d+$', server_name):
                base_name = re.sub(r'\d+$', '', server_name)
                if base_name and base_name != server_name:
                    servers.append(base_name)

            meta = {
                "servers": servers,
                "tags": ["server", "infrastructure"],
            }

        # Extract title
        title = None
        for line in body.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break

        return {
            "title": title or os.path.basename(file_path),
            "body": body,
            "tags": " ".join(meta.get("tags", [])) if isinstance(meta.get("tags"), list)
                   else meta.get("tags", "") or "",
            "servers": " ".join(meta.get("servers", [])) if isinstance(meta.get("servers"), list)
                     else meta.get("servers", "") or "",
            "path": rel_path
        }

    def _create_schema(self):
        """Create Tantivy schema from configuration"""
        schema_builder = tantivy.SchemaBuilder()

        for field_name, field_config in self.config['schema_fields'].items():
            schema_builder.add_text_field(
                field_name,
                stored=True,
                tokenizer_name=field_config.get('tokenizer', 'en_stem')
            )

        return schema_builder.build()

    def _should_rebuild_index(self, data_dir):
        """Check if index needs to be rebuilt based on file modifications"""
        index_info_path = os.path.join(data_dir, 'index_info.json')

        if not os.path.exists(index_info_path):
            return True

        try:
            with open(index_info_path, 'r') as f:
                index_info = json.load(f)

            # Check if any indexed file was modified
            for file_path in index_info.get('files', []):
                if os.path.exists(file_path):
                    file_mtime = os.path.getmtime(file_path)
                    if file_mtime > index_info.get('timestamp', 0):
                        return True
                else:
                    # File was deleted
                    return True

            return False
        except:
            return True

    def index_command(self, force=False):
        """Create or update document index"""
        print("🔍 Starting document indexing...")

        # Ensure data directory exists
        data_dir = self._ensure_data_dir()
        index_dir = os.path.join(data_dir, 'idx')

        # Check if rebuild is needed
        if not force and not self._should_rebuild_index(data_dir):
            print("✅ Index is up to date")
            return

        # Get files to index
        files = self._get_files_for_indexing()
        if not files:
            print("⚠️  No files found to index")
            return

        print(f"📁 Found {len(files)} files to index")

        # Parse documents
        docs = []
        for file_path in files:
            doc = self._parse_markdown(file_path)
            if doc:
                docs.append(doc)

        if not docs:
            print("⚠️  No valid documents found")
            return

        # Remove old index and create new directory
        if os.path.exists(index_dir):
            shutil.rmtree(index_dir)
        os.makedirs(index_dir, exist_ok=True)

        # Create schema and index
        schema = self._create_schema()
        index = tantivy.Index(schema, path=index_dir)

        # Index documents
        print(f"📝 Indexing {len(docs)} documents...")
        writer = index.writer()

        for doc_data in docs:
            writer.add_document(tantivy.Document(**doc_data))

        writer.commit()

        # Save index info
        index_info = {
            'timestamp': time.time(),
            'files': files,
            'count': len(docs)
        }

        with open(os.path.join(data_dir, 'index_info.json'), 'w') as f:
            json.dump(index_info, f, indent=2)

        print(f"✅ Successfully indexed {len(docs)} documents")
        print(f"📍 Index saved to: {index_dir}")
        print("💡 You can now search with: python tantivy-agent.py search 'your query'")

    def search_command(self, query, limit=None, format_output=None, output_file=None):
        """Search in indexed documents"""
        if not query:
            print("❌ Please provide a search query")
            return

        data_dir = os.path.join(self.project_root, self.config['index_dir'])
        index_dir = os.path.join(data_dir, 'idx')

        if not os.path.exists(index_dir):
            print("❌ Index not found. Run 'python tantivy-agent.py index' first")
            return

        try:
            # Load index
            index = tantivy.Index.open(index_dir)
            searcher = index.searcher()

            # Parse query
            field_names = list(self.config['schema_fields'].keys())
            query_parser = index.parse_query(query, field_names)

            # Search
            limit = limit or self.config['search']['default_limit']
            search_limit = limit * 4  # Get more results for filtering
            result = searcher.search(query_parser, search_limit)

            if not result.hits:
                print("🔍 No results found")
                return

            # Process results
            results_with_docs = []
            for score, doc_address in result.hits:
                doc = searcher.doc(doc_address)
                results_with_docs.append((score, doc_address, doc))

            # Apply filters
            filtered_results = self._apply_filters(results_with_docs, query)

            if not filtered_results:
                print("🔍 No results found after filtering")
                return

            # Export or display results
            if format_output:
                self._export_results(filtered_results[:limit], query, format_output, output_file)
            else:
                self._display_results(filtered_results[:limit])

        except Exception as e:
            print(f"❌ Search error: {e}")

    def _display_results(self, results):
        """Display results in standard format"""
        print(f"🎯 Found {len(results)} results:")
        print()

        for score, doc_address, doc in results:
            path = doc["path"][0]
            title = doc["title"][0] if doc["title"] else "No title"
            print(f"📄 {path}")
            print(f"   {title}")
            print(f"   [score: {score:.3f}]")
            print()

    def _export_results(self, results, query, format_output, output_file):
        """Export results in specified format"""
        if format_output.lower() == 'json':
            self._export_json(results, query, output_file)
        elif format_output.lower() == 'csv':
            self._export_csv(results, query, output_file)
        elif format_output.lower() == 'txt':
            self._export_txt(results, query, output_file)
        else:
            print(f"❌ Unsupported format: {format_output}")
            print("💡 Supported formats: json, csv, txt")
            return

    def _export_json(self, results, query, output_file):
        """Export results as JSON"""
        import json
        from datetime import datetime

        export_data = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "total_results": len(results),
            "results": []
        }

        for score, doc_address, doc in results:
            result_item = {
                "score": round(score, 4),
                "path": doc["path"][0] if doc["path"] else "",
                "title": doc["title"][0] if doc["title"] else "No title",
                "body": doc["body"][0] if doc["body"] else "",
                "tags": doc["tags"][0] if doc["tags"] else "",
                "servers": doc["servers"][0] if doc["servers"] else ""
            }
            export_data["results"].append(result_item)

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            print(f"✅ Results exported to {output_file}")
        else:
            print(json.dumps(export_data, indent=2, ensure_ascii=False))

    def _export_csv(self, results, query, output_file):
        """Export results as CSV"""
        import csv
        from datetime import datetime
        import sys

        if output_file:
            file_handle = open(output_file, 'w', newline='', encoding='utf-8')
        else:
            file_handle = sys.stdout

        try:
            writer = csv.writer(file_handle)

            # Write header
            writer.writerow(['Score', 'Path', 'Title', 'Tags', 'Servers'])

            # Write results
            for score, doc_address, doc in results:
                row = [
                    f"{score:.4f}",
                    doc["path"][0] if doc["path"] else "",
                    doc["title"][0] if doc["title"] else "No title",
                    doc["tags"][0] if doc["tags"] else "",
                    doc["servers"][0] if doc["servers"] else ""
                ]
                writer.writerow(row)

            if output_file:
                print(f"✅ Results exported to {output_file}")
            else:
                print()  # Add newline after CSV output

        finally:
            if output_file:
                file_handle.close()

    def _export_txt(self, results, query, output_file):
        """Export results as plain text"""
        from datetime import datetime

        if output_file:
            file_handle = open(output_file, 'w', encoding='utf-8')
        else:
            import sys
            file_handle = sys.stdout

        try:
            file_handle.write(f"Search Results for: '{query}'\n")
            file_handle.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            file_handle.write(f"Total Results: {len(results)}\n")
            file_handle.write("=" * 60 + "\n\n")

            for i, (score, doc_address, doc) in enumerate(results, 1):
                path = doc["path"][0] if doc["path"] else ""
                title = doc["title"][0] if doc["title"] else "No title"
                body = doc["body"][0] if doc["body"] else ""
                tags = doc["tags"][0] if doc["tags"] else ""
                servers = doc["servers"][0] if doc["servers"] else ""

                file_handle.write(f"{i}. {title}\n")
                file_handle.write(f"   Path: {path}\n")
                file_handle.write(f"   Score: {score:.4f}\n")

                if tags:
                    file_handle.write(f"   Tags: {tags}\n")
                if servers:
                    file_handle.write(f"   Servers: {servers}\n")

                # Add snippet of body (first 200 characters)
                if body:
                    snippet = body.replace('\n', ' ')[:200]
                    if len(body) > 200:
                        snippet += "..."
                    file_handle.write(f"   Preview: {snippet}\n")

                file_handle.write("\n")

            if output_file:
                print(f"✅ Results exported to {output_file}")

        finally:
            if output_file:
                file_handle.close()

    def _apply_filters(self, results, query):
        """Apply filters to search results"""
        query_words = set(query.lower().split())
        filtered = []

        # Incident filtering
        hide_incidents = self.config['search'].get('hide_incidents', True)
        show_incidents_on = self.config['search'].get('show_incidents_on', ['incident'])

        for score, doc_address, doc in results:
            file_path = doc["path"][0]

            # Hide incidents unless keyword is in query
            if hide_incidents and file_path.startswith("incidents/"):
                if not any(keyword in query_words for keyword in show_incidents_on):
                    continue

            filtered.append((score, doc_address, doc))

        return filtered

    def clear_command(self):
        """Clear the index"""
        print("🗑️  Clearing index...")

        data_dir = os.path.join(self.project_root, self.config['index_dir'])

        if os.path.exists(data_dir):
            shutil.rmtree(data_dir)
            print(f"✅ Cleared index directory: {data_dir}")
        else:
            print("ℹ️  No index directory found")

    def install_command(self):
        """Install Claude hooks and setup"""
        print("🔧 Installing Tantivy Agent...")

        # Ensure data directory
        self._ensure_data_dir()

        # Install Claude hooks if enabled
        if self.config.get('auto_hook', True):
            self._install_claude_hooks()

        print("✅ Installation complete!")
        print("💡 Run 'python tantivy-agent.py index' to create your first index")

    def _install_claude_hooks(self):
        """Install Claude Code hooks"""
        claude_dir = os.path.join(self.project_root, '.claude')
        os.makedirs(claude_dir, exist_ok=True)

        claude_config_path = os.path.join(claude_dir, 'CLAUDE.md')

        # Find where this script is located
        script_path = os.path.abspath(__file__)

        hook_config = f"""hooks:
  PostToolUse:
    - matcher: "Edit|Write|MultiEdit"
      hooks:
        - type: "command"
          command: "{script_path} hook-clear"
"""

        # Read existing config if it exists
        existing_config = ""
        if os.path.exists(claude_config_path):
            with open(claude_config_path, 'r', encoding='utf-8') as f:
                existing_config = f.read()

        # Check if hooks are already configured
        if "PostToolUse" in existing_config and "tantivy-agent" in existing_config:
            print("ℹ️  Claude hooks already installed")
            return

        # Append hooks to config
        with open(claude_config_path, 'a', encoding='utf-8') as f:
            if existing_config and not existing_config.endswith('\n'):
                f.write('\n')
            f.write('\n# Tantivy Agent hooks\n')
            f.write(hook_config)

        print("✅ Claude hooks installed")

    def hook_clear_command(self):
        """Clear index when files are modified (used by Claude hooks)"""
        # This is called by Claude hooks - check if any indexed files were modified
        # For now, just clear the index to be safe
        data_dir = os.path.join(self.project_root, self.config['index_dir'])

        if os.path.exists(data_dir):
            index_info_path = os.path.join(data_dir, 'index_info.json')
            if os.path.exists(index_info_path):
                # Mark index as outdated instead of deleting
                with open(index_info_path, 'r+') as f:
                    index_info = json.load(f)
                    index_info['outdated'] = True
                    f.seek(0)
                    json.dump(index_info, f, indent=2)
                    f.truncate()
            else:
                # No index info, remove directory
                shutil.rmtree(data_dir)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Universal Tantivy Agent - Document indexing and search',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tantivy-agent.py index
  python tantivy-agent.py search "my query"
  python tantivy-agent.py search "my query" --limit 5
  python tantivy-agent.py search "server" --format json --output results.json
  python tantivy-agent.py search "config" --format csv -o search_results.csv
  python tantivy-agent.py clear
  python tantivy-agent.py install
        """
    )

    parser.add_argument('command',
                       choices=['index', 'search', 'clear', 'install', 'hook-clear'],
                       help='Command to execute')

    parser.add_argument('query', nargs='*', help='Search query (for search command)')
    parser.add_argument('--limit', type=int, help='Number of search results')
    parser.add_argument('--force', action='store_true', help='Force rebuild index')
    parser.add_argument('--config', help='Path to config file')
    parser.add_argument('--format', choices=['json', 'csv', 'txt'],
                       help='Export results in specified format')
    parser.add_argument('--output', '-o', help='Output file for exported results')

    args = parser.parse_args()

    # Initialize agent
    agent = TantivyAgent(args.config)

    # Execute command
    if args.command == 'index':
        agent.index_command(force=args.force)
    elif args.command == 'search':
        query = ' '.join(args.query) if args.query else ''
        agent.search_command(query, args.limit, args.format, args.output)
    elif args.command == 'clear':
        agent.clear_command()
    elif args.command == 'install':
        agent.install_command()
    elif args.command == 'hook-clear':
        agent.hook_clear_command()


if __name__ == "__main__":
    main()