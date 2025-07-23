# Enhanced Cross-Reference Integration System
# File: enhanced_cross_reference_integrator.py
# Purpose: Link related information across modular data structure for better embeddings
# Tags: cross-references, data-integration, embeddings, RAG

import yaml
import os
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple
import logging
from data_loader import DataManager
import re

class EnhancedCrossReferenceIntegrator:
    """
    Enhanced cross-reference integrator with better pattern matching and debugging.
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_manager = DataManager(data_dir)
        self.logger = logging.getLogger(__name__)
        
        # Enhanced cross-reference patterns with more specific keywords
        self.cross_reference_patterns = {
            'values': {
                'projects': ['freedom', 'autonomy', 'independence', 'sovereignty', 'liberty', 'innovation', 'creativity'],
                'career': ['work', 'career', 'professional', 'job', 'employment'],
                'preferences': ['love', 'enjoy', 'favorite', 'resonates', 'themes'],
                'personality': ['trait', 'characteristic', 'behavior', 'style']
            },
            'personality': {
                'career': ['work', 'professional', 'job', 'leadership', 'communication'],
                'projects': ['approach', 'method', 'style', 'collaboration'],
                'technical_skills': ['learning', 'problem', 'solving', 'analytical'],
                'interests': ['curiosity', 'learning', 'interest', 'passion']
            },
            'projects': {
                'technical_skills': ['python', 'javascript', 'react', 'node', 'ai', 'bitcoin', 'technology'],
                'values': ['freedom', 'innovation', 'autonomy', 'creativity'],
                'career': ['career', 'professional', 'work', 'experience'],
                'interests': ['interest', 'passion', 'curiosity', 'learning']
            },
            'preferences': {
                'personality': ['emotional', 'aesthetic', 'style', 'tone'],
                'values': ['themes', 'philosophical', 'meaning', 'purpose'],
                'interests': ['curiosity', 'learning', 'interest'],
                'career': ['professional', 'work', 'balance']
            },
            'technical_skills': {
                'projects': ['project', 'application', 'development', 'implementation'],
                'career': ['professional', 'work', 'experience', 'development'],
                'personality': ['learning', 'analytical', 'problem', 'solving'],
                'interests': ['curiosity', 'learning', 'technology']
            },
            'interests': {
                'projects': ['project', 'development', 'creation', 'building'],
                'preferences': ['aesthetic', 'style', 'taste', 'enjoyment'],
                'career': ['professional', 'career', 'work', 'direction'],
                'values': ['motivation', 'purpose', 'meaning', 'philosophy']
            },
            'career': {
                'technical_skills': ['skill', 'technology', 'programming', 'development'],
                'projects': ['project', 'work', 'development', 'implementation'],
                'values': ['philosophy', 'values', 'principles', 'motivation'],
                'personality': ['style', 'approach', 'behavior', 'trait']
            }
        }
    
    def debug_data_structure(self):
        """Debug the data structure to understand what's available."""
        print("=== DEBUG: Data Structure Analysis ===")
        
        for category in self.cross_reference_patterns.keys():
            print(f"\n--- {category.upper()} ---")
            category_data = self.data_manager.get_category(category)
            
            if not category_data:
                print(f"  No data found for category: {category}")
                continue
            
            for file_name, content in category_data.items():
                print(f"  File: {file_name}")
                if isinstance(content, dict):
                    print(f"    Keys: {list(content.keys())}")
                    # Show a sample of the content
                    for key, value in list(content.items())[:3]:
                        if isinstance(value, list):
                            print(f"    {key}: {len(value)} items")
                        elif isinstance(value, dict):
                            print(f"    {key}: {len(value)} sub-keys")
                        else:
                            print(f"    {key}: {str(value)[:100]}...")
                else:
                    print(f"    Type: {type(content)}")
    
    def identify_cross_references(self) -> Dict[str, List[Dict[str, Any]]]:
        """Identify potential cross-references across all data categories."""
        cross_references = {}
        
        # Load all data
        all_data = {}
        for category in self.cross_reference_patterns.keys():
            all_data[category] = self.data_manager.get_category(category)
        
        print(f"Loaded data for categories: {list(all_data.keys())}")
        
        # Identify cross-references for each category pair
        for source_category, target_categories in self.cross_reference_patterns.items():
            for target_category, keywords in target_categories.items():
                key = f"{source_category}_to_{target_category}"
                cross_references[key] = []
                
                source_data = all_data.get(source_category, {})
                target_data = all_data.get(target_category, {})
                
                print(f"\nChecking {key}:")
                print(f"  Source files: {list(source_data.keys())}")
                print(f"  Target files: {list(target_data.keys())}")
                
                # Find cross-references based on keywords
                for keyword in keywords:
                    refs = self._find_keyword_matches(
                        source_data, target_data, keyword, source_category, target_category
                    )
                    cross_references[key].extend(refs)
                    if refs:
                        print(f"  Found {len(refs)} connections for keyword '{keyword}'")
        
        return cross_references
    
    def _find_keyword_matches(self, source_data: Dict, target_data: Dict, 
                            keyword: str, source_category: str, target_category: str) -> List[Dict[str, Any]]:
        """Find matches for a specific keyword between source and target data."""
        matches = []
        
        for source_file, source_content in source_data.items():
            source_text = self._extract_searchable_text(source_content)
            if keyword.lower() in source_text.lower():
                for target_file, target_content in target_data.items():
                    target_text = self._extract_searchable_text(target_content)
                    if keyword.lower() in target_text.lower():
                        matches.append({
                            'source_category': source_category,
                            'source_file': source_file,
                            'target_category': target_category,
                            'target_file': target_file,
                            'connection_type': 'keyword_match',
                            'keyword': keyword,
                            'relevance_score': 0.7,
                            'description': f"Keyword '{keyword}' connects {source_file} to {target_file}"
                        })
        
        return matches
    
    def _extract_searchable_text(self, data: Any) -> str:
        """Extract searchable text from nested data structures."""
        if isinstance(data, dict):
            text_parts = []
            for key, value in data.items():
                if key != 'metadata':  # Skip metadata
                    text_parts.append(str(value))
            return ' '.join(text_parts)
        elif isinstance(data, list):
            return ' '.join(str(item) for item in data)
        else:
            return str(data)
    
    def find_specific_connections(self) -> List[Dict[str, Any]]:
        """Find specific connections based on known data patterns."""
        connections = []
        
        # Get specific data for pattern matching
        all_data = {}
        for category in self.cross_reference_patterns.keys():
            all_data[category] = self.data_manager.get_category(category)
        
        # Find Python connections
        python_connections = self._find_python_connections(all_data)
        connections.extend(python_connections)
        
        # Find Bitcoin connections
        bitcoin_connections = self._find_bitcoin_connections(all_data)
        connections.extend(bitcoin_connections)
        
        # Find AI connections
        ai_connections = self._find_ai_connections(all_data)
        connections.extend(ai_connections)
        
        # Find freedom/autonomy connections
        freedom_connections = self._find_freedom_connections(all_data)
        connections.extend(freedom_connections)
        
        return connections
    
    def _find_python_connections(self, all_data: Dict) -> List[Dict[str, Any]]:
        """Find connections related to Python."""
        connections = []
        
        # Check technical_skills for Python
        tech_skills = all_data.get('career', {}).get('technical_skills', {})
        if tech_skills:
            tech_text = self._extract_searchable_text(tech_skills)
            if 'python' in tech_text.lower():
                # Find projects that use Python
                projects_data = all_data.get('personal', {}).get('projects', {})
                if projects_data:
                    projects_text = self._extract_searchable_text(projects_data)
                    if 'python' in projects_text.lower():
                        connections.append({
                            'source_category': 'career',
                            'source_file': 'technical_skills',
                            'target_category': 'personal',
                            'target_file': 'projects',
                            'connection_type': 'technology_skill',
                            'technology': 'Python',
                            'relevance_score': 0.9,
                            'description': 'Python skill connects technical_skills to projects'
                        })
        
        return connections
    
    def _find_bitcoin_connections(self, all_data: Dict) -> List[Dict[str, Any]]:
        """Find connections related to Bitcoin."""
        connections = []
        
        # Check various categories for Bitcoin mentions
        bitcoin_keywords = ['bitcoin', 'btc', 'cryptocurrency', 'blockchain']
        
        for category, category_data in all_data.items():
            for file_name, content in category_data.items():
                content_text = self._extract_searchable_text(content)
                if any(keyword in content_text.lower() for keyword in bitcoin_keywords):
                    # Find other files with Bitcoin mentions
                    for other_category, other_category_data in all_data.items():
                        for other_file, other_content in other_category_data.items():
                            if category != other_category or file_name != other_file:
                                other_text = self._extract_searchable_text(other_content)
                                if any(keyword in other_text.lower() for keyword in bitcoin_keywords):
                                    connections.append({
                                        'source_category': category,
                                        'source_file': file_name,
                                        'target_category': other_category,
                                        'target_file': other_file,
                                        'connection_type': 'bitcoin_interest',
                                        'relevance_score': 0.8,
                                        'description': f'Bitcoin interest connects {file_name} to {other_file}'
                                    })
        
        return connections
    
    def _find_ai_connections(self, all_data: Dict) -> List[Dict[str, Any]]:
        """Find connections related to AI."""
        connections = []
        
        ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'llm', 'rag']
        
        for category, category_data in all_data.items():
            for file_name, content in category_data.items():
                content_text = self._extract_searchable_text(content)
                if any(keyword in content_text.lower() for keyword in ai_keywords):
                    for other_category, other_category_data in all_data.items():
                        for other_file, other_content in other_category_data.items():
                            if category != other_category or file_name != other_file:
                                other_text = self._extract_searchable_text(other_content)
                                if any(keyword in other_text.lower() for keyword in ai_keywords):
                                    connections.append({
                                        'source_category': category,
                                        'source_file': file_name,
                                        'target_category': other_category,
                                        'target_file': other_file,
                                        'connection_type': 'ai_interest',
                                        'relevance_score': 0.8,
                                        'description': f'AI interest connects {file_name} to {other_file}'
                                    })
        
        return connections
    
    def _find_freedom_connections(self, all_data: Dict) -> List[Dict[str, Any]]:
        """Find connections related to freedom and autonomy."""
        connections = []
        
        freedom_keywords = ['freedom', 'autonomy', 'independence', 'sovereignty', 'liberty']
        
        for category, category_data in all_data.items():
            for file_name, content in category_data.items():
                content_text = self._extract_searchable_text(content)
                if any(keyword in content_text.lower() for keyword in freedom_keywords):
                    for other_category, other_category_data in all_data.items():
                        for other_file, other_content in other_category_data.items():
                            if category != other_category or file_name != other_file:
                                other_text = self._extract_searchable_text(other_content)
                                if any(keyword in other_text.lower() for keyword in freedom_keywords):
                                    connections.append({
                                        'source_category': category,
                                        'source_file': file_name,
                                        'target_category': other_category,
                                        'target_file': other_file,
                                        'connection_type': 'freedom_value',
                                        'relevance_score': 0.85,
                                        'description': f'Freedom value connects {file_name} to {other_file}'
                                    })
        
        return connections
    
    def integrate_cross_references(self, connections: List[Dict[str, Any]]) -> None:
        """Integrate cross-references into the existing data structure."""
        for connection in connections:
            self._add_cross_reference(connection)
    
    def _add_cross_reference(self, connection: Dict[str, Any]) -> None:
        """Add a single cross-reference to the appropriate files."""
        source_category = connection['source_category']
        source_file = connection['source_file']
        target_category = connection['target_category']
        target_file = connection['target_file']
        
        # Add cross-reference to source file
        source_path = self.data_dir / source_category / f"{source_file}.yaml"
        if source_path.exists():
            self._add_reference_to_file(source_path, connection, 'source')
        
        # Add cross-reference to target file
        target_path = self.data_dir / target_category / f"{target_file}.yaml"
        if target_path.exists():
            self._add_reference_to_file(target_path, connection, 'target')
    
    def _add_reference_to_file(self, file_path: Path, connection: Dict[str, Any], ref_type: str) -> None:
        """Add cross-reference to a specific YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
            
            # Initialize cross_references section if it doesn't exist
            if 'cross_references' not in data:
                data['cross_references'] = []
            
            # Create reference entry
            if ref_type == 'source':
                ref_entry = {
                    'type': 'outgoing',
                    'target_category': connection['target_category'],
                    'target_file': connection['target_file'],
                    'connection_type': connection['connection_type'],
                    'relevance_score': connection['relevance_score'],
                    'description': connection['description']
                }
            else:  # target
                ref_entry = {
                    'type': 'incoming',
                    'source_category': connection['source_category'],
                    'source_file': connection['source_file'],
                    'connection_type': connection['connection_type'],
                    'relevance_score': connection['relevance_score'],
                    'description': connection['description']
                }
            
            # Add specific connection details
            for key in ['technology', 'keyword']:
                if key in connection:
                    ref_entry[key] = connection[key]
            
            data['cross_references'].append(ref_entry)
            
            # Save updated file
            with open(file_path, 'w', encoding='utf-8') as file:
                yaml.dump(data, file, default_flow_style=False, sort_keys=False, indent=2)
            
            self.logger.info(f"Added cross-reference to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error adding cross-reference to {file_path}: {e}")
    
    def generate_cross_reference_report(self, connections: List[Dict[str, Any]]) -> str:
        """Generate a report of all cross-references."""
        report = "# Enhanced Cross-Reference Integration Report\n\n"
        
        if not connections:
            report += "No cross-references found.\n\n"
        else:
            # Group by connection type
            by_type = {}
            for connection in connections:
                conn_type = connection['connection_type']
                if conn_type not in by_type:
                    by_type[conn_type] = []
                by_type[conn_type].append(connection)
            
            for conn_type, conns in by_type.items():
                report += f"## {conn_type.replace('_', ' ').title()}\n"
                report += f"**Total Connections**: {len(conns)}\n\n"
                
                for connection in conns:
                    report += f"- **{connection['source_file']}** → **{connection['target_file']}**\n"
                    report += f"  - Description: {connection['description']}\n"
                    report += f"  - Relevance: {connection['relevance_score']}\n"
                    if 'technology' in connection:
                        report += f"  - Technology: {connection['technology']}\n"
                    if 'keyword' in connection:
                        report += f"  - Keyword: {connection['keyword']}\n"
                    report += "\n"
        
        report += f"## Summary\n"
        report += f"- **Total Cross-References**: {len(connections)}\n"
        report += f"- **Connection Types**: {len(set(c['connection_type'] for c in connections))}\n"
        
        return report
    
    def run_integration(self) -> str:
        """Run the complete cross-reference integration process."""
        self.logger.info("Starting enhanced cross-reference integration...")
        
        # Step 1: Debug data structure
        self.debug_data_structure()
        
        # Step 2: Find specific connections
        connections = self.find_specific_connections()
        
        # Step 3: Integrate cross-references into files
        self.integrate_cross_references(connections)
        
        # Step 4: Generate report
        report = self.generate_cross_reference_report(connections)
        
        self.logger.info("Enhanced cross-reference integration completed!")
        return report


def main():
    """Run the enhanced cross-reference integration."""
    integrator = EnhancedCrossReferenceIntegrator()
    report = integrator.run_integration()
    
    # Save report
    with open('enhanced_cross_reference_report.md', 'w') as f:
        f.write(report)
    
    print("Enhanced cross-reference integration completed!")
    print(f"Report saved to: enhanced_cross_reference_report.md")
    print(f"\nSummary of report:\n{report.split('## Summary')[1]}")


if __name__ == "__main__":
    main() 