# Cross-Reference Integration System
# File: cross_reference_integrator.py
# Purpose: Link related information across modular data structure for better embeddings
# Tags: cross-references, data-integration, embeddings, RAG

import yaml
import os
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple
import logging
from data_loader import DataManager

class CrossReferenceIntegrator:
    """
    Integrates cross-references across the modular data structure to improve
    embeddings and RAG performance by creating semantic connections between
    related information.
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_manager = DataManager(data_dir)
        self.logger = logging.getLogger(__name__)
        
        # Define cross-reference patterns
        self.cross_reference_patterns = {
            'values': {
                'projects': ['freedom', 'innovation', 'autonomy', 'creativity'],
                'career': ['work_philosophy', 'career_decisions', 'professional_values'],
                'preferences': ['themes', 'emotional_resonance', 'philosophical_alignment'],
                'personality': ['trait_manifestation', 'behavioral_patterns']
            },
            'personality': {
                'career': ['work_style', 'communication_preferences', 'leadership_style'],
                'projects': ['approach_to_problem_solving', 'collaboration_style'],
                'technical_skills': ['learning_style', 'problem_solving_approach'],
                'interests': ['curiosity_patterns', 'learning_preferences']
            },
            'projects': {
                'technical_skills': ['technologies_used', 'skill_development'],
                'values': ['project_motivation', 'underlying_principles'],
                'career': ['career_impact', 'skill_application'],
                'interests': ['interest_manifestation', 'passion_projects']
            },
            'preferences': {
                'personality': ['emotional_resonance', 'aesthetic_preferences'],
                'values': ['thematic_alignment', 'philosophical_connection'],
                'interests': ['intellectual_curiosity', 'learning_interests'],
                'career': ['professional_interests', 'work_life_balance']
            },
            'technical_skills': {
                'projects': ['skill_application', 'technology_choices'],
                'career': ['professional_development', 'skill_evolution'],
                'personality': ['learning_style', 'problem_solving_approach'],
                'interests': ['technical_curiosity', 'skill_development']
            },
            'interests': {
                'projects': ['interest_manifestation', 'passion_projects'],
                'preferences': ['aesthetic_alignment', 'intellectual_curiosity'],
                'career': ['professional_interests', 'career_direction'],
                'values': ['underlying_motivations', 'philosophical_alignment']
            },
            'career': {
                'technical_skills': ['skill_development', 'professional_application'],
                'projects': ['career_impact', 'skill_transfer'],
                'values': ['work_philosophy', 'career_decisions'],
                'personality': ['work_style', 'professional_relationships']
            }
        }
    
    def identify_cross_references(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Identify potential cross-references across all data categories.
        
        Returns:
            Dictionary mapping category pairs to lists of cross-references
        """
        cross_references = {}
        
        # Load all data
        all_data = {}
        for category in self.cross_reference_patterns.keys():
            all_data[category] = self.data_manager.get_category(category)
        
        # Identify cross-references for each category pair
        for source_category, target_categories in self.cross_reference_patterns.items():
            for target_category, patterns in target_categories.items():
                key = f"{source_category}_to_{target_category}"
                cross_references[key] = []
                
                source_data = all_data.get(source_category, {})
                target_data = all_data.get(target_category, {})
                
                # Find cross-references based on patterns
                for pattern in patterns:
                    refs = self._find_pattern_matches(
                        source_data, target_data, pattern, source_category, target_category
                    )
                    cross_references[key].extend(refs)
        
        return cross_references
    
    def _find_pattern_matches(self, source_data: Dict, target_data: Dict, 
                            pattern: str, source_category: str, target_category: str) -> List[Dict[str, Any]]:
        """Find matches for a specific pattern between source and target data."""
        matches = []
        
        # Convert data to searchable text
        source_text = self._flatten_data(source_data)
        target_text = self._flatten_data(target_data)
        
        # Find semantic matches based on pattern
        if pattern == 'freedom':
            matches.extend(self._find_freedom_connections(source_data, target_data, source_category, target_category))
        elif pattern == 'innovation':
            matches.extend(self._find_innovation_connections(source_data, target_data, source_category, target_category))
        elif pattern == 'technical_skills':
            matches.extend(self._find_technical_connections(source_data, target_data, source_category, target_category))
        elif pattern == 'projects':
            matches.extend(self._find_project_connections(source_data, target_data, source_category, target_category))
        elif pattern == 'personality_traits':
            matches.extend(self._find_personality_connections(source_data, target_data, source_category, target_category))
        elif pattern == 'values':
            matches.extend(self._find_value_connections(source_data, target_data, source_category, target_category))
        
        return matches
    
    def _find_freedom_connections(self, source_data: Dict, target_data: Dict, 
                                source_category: str, target_category: str) -> List[Dict[str, Any]]:
        """Find connections related to freedom and autonomy."""
        connections = []
        
        # Look for freedom-related content in source
        freedom_keywords = ['freedom', 'autonomy', 'independence', 'sovereignty', 'liberty']
        
        for source_file, source_content in source_data.items():
            source_text = str(source_content).lower()
            if any(keyword in source_text for keyword in freedom_keywords):
                # Find related content in target
                for target_file, target_content in target_data.items():
                    target_text = str(target_content).lower()
                    if any(keyword in target_text for keyword in freedom_keywords):
                        connections.append({
                            'source_category': source_category,
                            'source_file': source_file,
                            'target_category': target_category,
                            'target_file': target_file,
                            'connection_type': 'freedom_autonomy',
                            'relevance_score': 0.9,
                            'description': f"Freedom/autonomy theme connects {source_file} to {target_file}"
                        })
        
        return connections
    
    def _find_innovation_connections(self, source_data: Dict, target_data: Dict,
                                   source_category: str, target_category: str) -> List[Dict[str, Any]]:
        """Find connections related to innovation and creativity."""
        connections = []
        
        innovation_keywords = ['innovation', 'creativity', 'novel', 'breakthrough', 'inventive', 'creative']
        
        for source_file, source_content in source_data.items():
            source_text = str(source_content).lower()
            if any(keyword in source_text for keyword in innovation_keywords):
                for target_file, target_content in target_data.items():
                    target_text = str(target_content).lower()
                    if any(keyword in target_text for keyword in innovation_keywords):
                        connections.append({
                            'source_category': source_category,
                            'source_file': source_file,
                            'target_category': target_category,
                            'target_file': target_file,
                            'connection_type': 'innovation_creativity',
                            'relevance_score': 0.85,
                            'description': f"Innovation/creativity theme connects {source_file} to {target_file}"
                        })
        
        return connections
    
    def _find_technical_connections(self, source_data: Dict, target_data: Dict,
                                  source_category: str, target_category: str) -> List[Dict[str, Any]]:
        """Find connections related to technical skills and technologies."""
        connections = []
        
        # Get technical skills from technical_skills data
        tech_skills = []
        if 'technical_skills' in self.data_manager.cache:
            tech_data = self.data_manager.cache['technical_skills']
            for file_name, content in tech_data.items():
                if 'programming_languages' in content:
                    for lang in content['programming_languages']:
                        if isinstance(lang, dict) and 'language' in lang:
                            tech_skills.append(lang['language'].lower())
                        elif isinstance(lang, str):
                            tech_skills.append(lang.lower())
        
        # Find technical connections
        for source_file, source_content in source_data.items():
            source_text = str(source_content).lower()
            for skill in tech_skills:
                if skill in source_text:
                    for target_file, target_content in target_data.items():
                        target_text = str(target_content).lower()
                        if skill in target_text:
                            connections.append({
                                'source_category': source_category,
                                'source_file': source_file,
                                'target_category': target_category,
                                'target_file': target_file,
                                'connection_type': 'technical_skill',
                                'skill': skill,
                                'relevance_score': 0.95,
                                'description': f"Technical skill '{skill}' connects {source_file} to {target_file}"
                            })
        
        return connections
    
    def _find_project_connections(self, source_data: Dict, target_data: Dict,
                                source_category: str, target_category: str) -> List[Dict[str, Any]]:
        """Find connections related to specific projects."""
        connections = []
        
        # Get project names from projects data
        project_names = []
        if 'projects' in self.data_manager.cache:
            projects_data = self.data_manager.cache['projects']
            for file_name, content in projects_data.items():
                if 'features' in content:
                    for feature in content['features']:
                        if isinstance(feature, dict) and 'project' in feature:
                            project_names.append(feature['project'].lower())
        
        # Find project connections
        for source_file, source_content in source_data.items():
            source_text = str(source_content).lower()
            for project in project_names:
                if project in source_text:
                    for target_file, target_content in target_data.items():
                        target_text = str(target_content).lower()
                        if project in target_text:
                            connections.append({
                                'source_category': source_category,
                                'source_file': source_file,
                                'target_category': target_category,
                                'target_file': target_file,
                                'connection_type': 'project_reference',
                                'project': project,
                                'relevance_score': 0.9,
                                'description': f"Project '{project}' connects {source_file} to {target_file}"
                            })
        
        return connections
    
    def _find_personality_connections(self, source_data: Dict, target_data: Dict,
                                    source_category: str, target_category: str) -> List[Dict[str, Any]]:
        """Find connections related to personality traits."""
        connections = []
        
        # Get personality traits from personality data
        personality_traits = []
        if 'personal' in self.data_manager.cache:
            personality_data = self.data_manager.cache['personal']
            if 'personality' in personality_data:
                personality_content = personality_data['personality']
                if 'traits' in personality_content:
                    for trait in personality_content['traits']:
                        if isinstance(trait, dict) and 'trait' in trait:
                            personality_traits.append(trait['trait'].lower())
        
        # Find personality connections
        for source_file, source_content in source_data.items():
            source_text = str(source_content).lower()
            for trait in personality_traits:
                if trait in source_text:
                    for target_file, target_content in target_data.items():
                        target_text = str(target_content).lower()
                        if trait in target_text:
                            connections.append({
                                'source_category': source_category,
                                'source_file': source_file,
                                'target_category': target_category,
                                'target_file': target_file,
                                'connection_type': 'personality_trait',
                                'trait': trait,
                                'relevance_score': 0.8,
                                'description': f"Personality trait '{trait}' connects {source_file} to {target_file}"
                            })
        
        return connections
    
    def _find_value_connections(self, source_data: Dict, target_data: Dict,
                              source_category: str, target_category: str) -> List[Dict[str, Any]]:
        """Find connections related to core values."""
        connections = []
        
        # Get core values from values data
        core_values = []
        if 'personal' in self.data_manager.cache:
            values_data = self.data_manager.cache['personal']
            if 'values' in values_data:
                values_content = values_data['values']
                if 'core_values' in values_content:
                    for value in values_content['core_values']:
                        if isinstance(value, dict) and 'value' in value:
                            core_values.append(value['value'].lower())
        
        # Find value connections
        for source_file, source_content in source_data.items():
            source_text = str(source_content).lower()
            for value in core_values:
                if value in source_text:
                    for target_file, target_content in target_data.items():
                        target_text = str(target_content).lower()
                        if value in target_text:
                            connections.append({
                                'source_category': source_category,
                                'source_file': source_file,
                                'target_category': target_category,
                                'target_file': target_file,
                                'connection_type': 'core_value',
                                'value': value,
                                'relevance_score': 0.85,
                                'description': f"Core value '{value}' connects {source_file} to {target_file}"
                            })
        
        return connections
    
    def _flatten_data(self, data: Dict) -> str:
        """Flatten nested data structure into searchable text."""
        if isinstance(data, dict):
            return ' '.join(str(v) for v in data.values())
        elif isinstance(data, list):
            return ' '.join(str(item) for item in data)
        else:
            return str(data)
    
    def integrate_cross_references(self, cross_references: Dict[str, List[Dict[str, Any]]]) -> None:
        """
        Integrate cross-references into the existing data structure.
        
        Args:
            cross_references: Dictionary of identified cross-references
        """
        for connection_key, connections in cross_references.items():
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
            if 'skill' in connection:
                ref_entry['skill'] = connection['skill']
            if 'project' in connection:
                ref_entry['project'] = connection['project']
            if 'trait' in connection:
                ref_entry['trait'] = connection['trait']
            if 'value' in connection:
                ref_entry['value'] = connection['value']
            
            data['cross_references'].append(ref_entry)
            
            # Save updated file
            with open(file_path, 'w', encoding='utf-8') as file:
                yaml.dump(data, file, default_flow_style=False, sort_keys=False, indent=2)
            
            self.logger.info(f"Added cross-reference to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error adding cross-reference to {file_path}: {e}")
    
    def generate_cross_reference_report(self, cross_references: Dict[str, List[Dict[str, Any]]]) -> str:
        """Generate a report of all cross-references."""
        report = "# Cross-Reference Integration Report\n\n"
        
        total_connections = 0
        for connection_key, connections in cross_references.items():
            if connections:
                report += f"## {connection_key.replace('_', ' ').title()}\n"
                report += f"**Total Connections**: {len(connections)}\n\n"
                
                for connection in connections:
                    report += f"- **{connection['connection_type']}**: {connection['description']}\n"
                    report += f"  - Relevance: {connection['relevance_score']}\n"
                    if 'skill' in connection:
                        report += f"  - Skill: {connection['skill']}\n"
                    if 'project' in connection:
                        report += f"  - Project: {connection['project']}\n"
                    if 'trait' in connection:
                        report += f"  - Trait: {connection['trait']}\n"
                    if 'value' in connection:
                        report += f"  - Value: {connection['value']}\n"
                    report += "\n"
                
                total_connections += len(connections)
        
        report += f"\n## Summary\n"
        report += f"- **Total Cross-References**: {total_connections}\n"
        report += f"- **Categories Connected**: {len([k for k, v in cross_references.items() if v])}\n"
        
        return report
    
    def run_integration(self) -> str:
        """Run the complete cross-reference integration process."""
        self.logger.info("Starting cross-reference integration...")
        
        # Step 1: Identify cross-references
        cross_references = self.identify_cross_references()
        
        # Step 2: Integrate cross-references into files
        self.integrate_cross_references(cross_references)
        
        # Step 3: Generate report
        report = self.generate_cross_reference_report(cross_references)
        
        self.logger.info("Cross-reference integration completed!")
        return report


def main():
    """Run the cross-reference integration."""
    integrator = CrossReferenceIntegrator()
    report = integrator.run_integration()
    
    # Save report
    with open('cross_reference_report.md', 'w') as f:
        f.write(report)
    
    print("Cross-reference integration completed!")
    print(f"Report saved to: cross_reference_report.md")
    print(f"\nSummary of report:\n{report.split('## Summary')[1]}")


if __name__ == "__main__":
    main() 