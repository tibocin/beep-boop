# Data Loader Utility
# File: data_loader.py
# Purpose: Load and manage modular YAML data for agentic companion knowledge base
# Tags: data-loading, yaml, modular, knowledge-base

import yaml
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

class DataManager:
    """
    Manages loading and caching of modular YAML data files for the agentic companion.
    
    Supports both eager loading (all data at startup) and lazy loading (on-demand)
    for optimal performance and memory usage.
    """
    
    def __init__(self, data_dir: str = "data", cache_enabled: bool = True):
        self.data_dir = Path(data_dir)
        self.cache_enabled = cache_enabled
        self.cache: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        
        # Define data categories and their file patterns
        self.categories = {
            'personal': ['values.yaml', 'personality.yaml', 'goals.yaml', 'interests.yaml'],
            'preferences': ['movies.yaml', 'shows.yaml', 'music.yaml', 'books.yaml', 'documentaries.yaml'],
            'career': ['work_experience.yaml', 'technical_skills.yaml', 'projects.yaml'],
            'projects': ['beep_boop.yaml', 'lumi.yaml', 'cvpunk.yaml', 'stackr.yaml', 'revao.yaml'],
            'metadata': ['session_meta.yaml', 'tags.yaml']
        }
        
        if cache_enabled:
            self._load_all_data()
    
    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load a single YAML file with error handling."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
                self.logger.info(f"Loaded {file_path}")
                return data
        except FileNotFoundError:
            self.logger.warning(f"File not found: {file_path}")
            return {}
        except yaml.YAMLError as e:
            self.logger.error(f"YAML parsing error in {file_path}: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Unexpected error loading {file_path}: {e}")
            return {}
    
    def _load_all_data(self):
        """Load all YAML files into cache."""
        self.logger.info("Loading all data files...")
        
        for category, files in self.categories.items():
            self.cache[category] = {}
            category_dir = self.data_dir / category
            
            for filename in files:
                file_path = category_dir / filename
                if file_path.exists():
                    data = self._load_yaml_file(file_path)
                    # Extract the main content (remove metadata for caching)
                    content = {k: v for k, v in data.items() if k != 'metadata'}
                    self.cache[category][filename.replace('.yaml', '')] = content
        
        self.logger.info(f"Loaded {len(self.cache)} categories with {sum(len(files) for files in self.cache.values())} files")
    
    def get_category(self, category: str) -> Dict[str, Any]:
        """Get all data for a specific category."""
        if not self.cache_enabled:
            return self._load_category_lazy(category)
        return self.cache.get(category, {})
    
    def get_file(self, category: str, filename: str) -> Dict[str, Any]:
        """Get data from a specific file."""
        if not self.cache_enabled:
            return self._load_file_lazy(category, filename)
        
        category_data = self.cache.get(category, {})
        return category_data.get(filename, {})
    
    def _load_category_lazy(self, category: str) -> Dict[str, Any]:
        """Lazy load a category of files."""
        category_data = {}
        category_dir = self.data_dir / category
        
        if not category_dir.exists():
            self.logger.warning(f"Category directory not found: {category_dir}")
            return category_data
        
        for file_path in category_dir.glob("*.yaml"):
            filename = file_path.stem
            data = self._load_yaml_file(file_path)
            content = {k: v for k, v in data.items() if k != 'metadata'}
            category_data[filename] = content
        
        return category_data
    
    def _load_file_lazy(self, category: str, filename: str) -> Dict[str, Any]:
        """Lazy load a specific file."""
        file_path = self.data_dir / category / f"{filename}.yaml"
        data = self._load_yaml_file(file_path)
        return {k: v for k, v in data.items() if k != 'metadata'}
    
    def search_content(self, query: str, categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Search across all content for specific terms.
        
        Args:
            query: Search term
            categories: Optional list of categories to search in
            
        Returns:
            List of matching content with metadata
        """
        results = []
        
        if categories is None:
            categories = list(self.categories.keys())
        
        for category in categories:
            category_data = self.get_category(category)
            
            for filename, content in category_data.items():
                # Simple text search (could be enhanced with more sophisticated search)
                content_str = str(content).lower()
                if query.lower() in content_str:
                    results.append({
                        'category': category,
                        'filename': filename,
                        'content': content,
                        'match_type': 'text_search'
                    })
        
        return results
    
    def get_metadata(self, category: str, filename: str) -> Dict[str, Any]:
        """Get metadata for a specific file."""
        file_path = self.data_dir / category / f"{filename}.yaml"
        data = self._load_yaml_file(file_path)
        return data.get('metadata', {})
    
    def list_files(self, category: Optional[str] = None) -> Dict[str, List[str]]:
        """List all available files, optionally filtered by category."""
        if category:
            return {category: list(self.cache.get(category, {}).keys())}
        
        return {cat: list(files.keys()) for cat, files in self.cache.items()}
    
    def reload_cache(self):
        """Reload all data from disk."""
        self.cache.clear()
        self._load_all_data()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded data."""
        stats = {
            'total_categories': len(self.categories),
            'total_files': sum(len(files) for files in self.cache.values()),
            'cache_enabled': self.cache_enabled,
            'categories': {}
        }
        
        for category, files in self.cache.items():
            stats['categories'][category] = {
                'file_count': len(files),
                'files': list(files.keys())
            }
        
        return stats


# Example usage and testing
def main():
    """Example usage of the DataManager."""
    # Initialize with caching enabled
    dm = DataManager(cache_enabled=True)
    
    # Get all personal data
    personal_data = dm.get_category('personal')
    print(f"Personal data categories: {list(personal_data.keys())}")
    
    # Get specific movie preferences
    movies = dm.get_file('preferences', 'movies')
    print(f"Movie categories: {list(movies.get('movies', {}).keys())}")
    
    # Search for content
    results = dm.search_content('spiritual')
    print(f"Found {len(results)} results for 'spiritual'")
    
    # Get statistics
    stats = dm.get_stats()
    print(f"Data stats: {stats}")


if __name__ == "__main__":
    main() 