# Data Structure Migration Script
# File: migrate_data_structure.py
# Purpose: Migrate from large YAML files to modular structure
# Tags: migration, data-structure, yaml, modular

import yaml
import os
from pathlib import Path
from typing import Dict, Any, List
import shutil

class DataMigrator:
    """
    Migrates large YAML files to modular structure for better maintainability.
    """
    
    def __init__(self, source_dir: str = "data", target_dir: str = "data_new"):
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        
        # Create target directory structure
        self._create_directory_structure()
    
    def _create_directory_structure(self):
        """Create the new modular directory structure."""
        directories = [
            'personal',
            'preferences', 
            'career',
            'projects',
            'metadata'
        ]
        
        for directory in directories:
            (self.target_dir / directory).mkdir(parents=True, exist_ok=True)
    
    def migrate_favorites(self):
        """Migrate favorites.yaml to separate preference files."""
        source_file = self.source_dir / "favorites.yaml"
        if not source_file.exists():
            print(f"Source file not found: {source_file}")
            return
        
        with open(source_file, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        
        favorites = data.get('favorites', {})
        
        # Extract movies
        if 'movies' in favorites:
            self._create_preference_file('movies', favorites['movies'])
        
        # Extract shows
        if 'shows' in favorites:
            self._create_preference_file('shows', favorites['shows'])
        
        # Extract music
        if 'music' in favorites:
            self._create_preference_file('music', favorites['music'])
        
        # Extract books
        if 'books' in favorites:
            self._create_preference_file('books', favorites['books'])
        
        # Extract documentaries
        if 'documentaries' in favorites:
            self._create_preference_file('documentaries', favorites['documentaries'])
    
    def migrate_session_summary(self):
        """Migrate enhanced_session1_summary.yaml to personal files."""
        source_file = self.source_dir / "enhanced_session1_summary.yaml"
        if not source_file.exists():
            print(f"Source file not found: {source_file}")
            return
        
        with open(source_file, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        
        # Extract values
        if 'values' in data:
            self._create_personal_file('values', data['values'])
        
        # Extract personality
        if 'personality' in data:
            self._create_personal_file('personality', data['personality'])
        
        # Extract projects
        if 'projects' in data:
            self._create_personal_file('projects', data['projects'])
        
        # Extract technical_skills
        if 'technical_skills' in data:
            self._create_career_file('technical_skills', data['technical_skills'])
        
        # Extract interests
        if 'interests' in data:
            self._create_personal_file('interests', data['interests'])
        
        # Extract work_experience
        if 'work_experience' in data:
            self._create_career_file('work_experience', data['work_experience'])
        
        # Extract personal_goals
        if 'personal_goals' in data:
            self._create_personal_file('goals', data['personal_goals'])
        
        # Extract session_meta
        if 'session_meta' in data:
            self._create_metadata_file('session_meta', data['session_meta'])
    
    def migrate_features(self):
        """Migrate features.yaml to project-specific files."""
        source_file = self.source_dir / "features.yaml"
        if not source_file.exists():
            print(f"Source file not found: {source_file}")
            return
        
        with open(source_file, 'r', encoding='utf-8') as file:
            features = yaml.safe_load(file)
        
        # Group features by project
        project_features = {}
        for feature in features:
            project = feature.get('project', 'unknown')
            if project not in project_features:
                project_features[project] = []
            project_features[project].append(feature)
        
        # Create project-specific files
        for project, features_list in project_features.items():
            self._create_project_file(project, features_list)
    
    def _create_preference_file(self, filename: str, data: Dict[str, Any]):
        """Create a preference file with metadata."""
        file_path = self.target_dir / 'preferences' / f"{filename}.yaml"
        
        content = {
            'metadata': {
                'file_type': 'preferences',
                'last_updated': '2025-01-22',
                'version': '1.0',
                'tags': [filename, 'preferences', 'entertainment'],
                'description': f'{filename.title()} preferences and analysis'
            },
            filename: data
        }
        
        with open(file_path, 'w', encoding='utf-8') as file:
            yaml.dump(content, file, default_flow_style=False, sort_keys=False, indent=2)
        
        print(f"Created: {file_path}")
    
    def _create_personal_file(self, filename: str, data: Dict[str, Any]):
        """Create a personal file with metadata."""
        file_path = self.target_dir / 'personal' / f"{filename}.yaml"
        
        content = {
            'metadata': {
                'file_type': 'personal',
                'last_updated': '2025-01-22',
                'version': '1.0',
                'tags': [filename, 'personal', 'profile'],
                'description': f'{filename.title()} information and characteristics'
            },
            filename: data
        }
        
        with open(file_path, 'w', encoding='utf-8') as file:
            yaml.dump(content, file, default_flow_style=False, sort_keys=False, indent=2)
        
        print(f"Created: {file_path}")
    
    def _create_career_file(self, filename: str, data: Dict[str, Any]):
        """Create a career file with metadata."""
        file_path = self.target_dir / 'career' / f"{filename}.yaml"
        
        content = {
            'metadata': {
                'file_type': 'career',
                'last_updated': '2025-01-22',
                'version': '1.0',
                'tags': [filename, 'career', 'professional'],
                'description': f'{filename.replace("_", " ").title()} information'
            },
            filename: data
        }
        
        with open(file_path, 'w', encoding='utf-8') as file:
            yaml.dump(content, file, default_flow_style=False, sort_keys=False, indent=2)
        
        print(f"Created: {file_path}")
    
    def _create_project_file(self, project: str, features: List[Dict[str, Any]]):
        """Create a project file with metadata."""
        file_path = self.target_dir / 'projects' / f"{project}.yaml"
        
        content = {
            'metadata': {
                'file_type': 'projects',
                'last_updated': '2025-01-22',
                'version': '1.0',
                'tags': [project, 'projects', 'features'],
                'description': f'{project.title()} project features and capabilities'
            },
            'features': features
        }
        
        with open(file_path, 'w', encoding='utf-8') as file:
            yaml.dump(content, file, default_flow_style=False, sort_keys=False, indent=2)
        
        print(f"Created: {file_path}")
    
    def _create_metadata_file(self, filename: str, data: Dict[str, Any]):
        """Create a metadata file."""
        file_path = self.target_dir / 'metadata' / f"{filename}.yaml"
        
        content = {
            'metadata': {
                'file_type': 'metadata',
                'last_updated': '2025-01-22',
                'version': '1.0',
                'tags': [filename, 'metadata'],
                'description': f'{filename.replace("_", " ").title()} metadata'
            },
            filename: data
        }
        
        with open(file_path, 'w', encoding='utf-8') as file:
            yaml.dump(content, file, default_flow_style=False, sort_keys=False, indent=2)
        
        print(f"Created: {file_path}")
    
    def copy_existing_files(self):
        """Copy files that are already appropriately sized."""
        files_to_copy = [
            ('work_experience.yaml', 'career'),
            ('beep-boop_project.yaml', 'projects')
        ]
        
        for filename, category in files_to_copy:
            source = self.source_dir / filename
            target = self.target_dir / category / filename
            
            if source.exists():
                shutil.copy2(source, target)
                print(f"Copied: {source} -> {target}")
    
    def run_migration(self):
        """Run the complete migration process."""
        print("Starting data structure migration...")
        
        # Migrate large files
        self.migrate_favorites()
        self.migrate_session_summary()
        self.migrate_features()
        
        # Copy appropriately sized files
        self.copy_existing_files()
        
        print(f"\nMigration complete! New structure created in: {self.target_dir}")
        print("\nNext steps:")
        print("1. Review the new structure")
        print("2. Test with data_loader.py")
        print("3. Update your application to use the new structure")
        print("4. Remove old files when ready")


def main():
    """Run the migration."""
    migrator = DataMigrator()
    migrator.run_migration()


if __name__ == "__main__":
    main() 