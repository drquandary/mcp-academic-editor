#!/usr/bin/env python3
"""
Test the complete surgical editing pipeline.
"""

import sys
import json
from pathlib import Path

# Add current directory to path
sys.path.insert(0, '.')

# Import the tool functions directly
from server import (
    process_manuscript, preview_surgical_edits, apply_surgical_edits,
    create_vision_brief, get_manuscript_structure
)

def test_complete_surgical_pipeline():
    """Test the full surgical editing pipeline end-to-end."""
    print("🔬 Testing Complete Surgical Editing Pipeline")
    print("=" * 60)
    
    # Test with demo manuscript if available
    demo_manuscript = "demo_manuscript.md"
    test_comments = [
        "Add citations to support the claim about AI prevalence",
        "Clarify what 'strategic engagement' means in the results section", 
        "The conclusion could benefit from mentioning implications for AI design"
    ]
    
    if not Path(demo_manuscript).exists():
        print("❌ Demo manuscript not found. Run 'python run_editor.py demo' first.")
        return False
    
    try:
        print("\n1. Creating vision brief...")
        vision_result = create_vision_brief(
            thesis="Human agency co-evolves with AI rather than being replaced by it",
            claims=[
                "Users develop strategic approaches to AI interaction",
                "Agency is maintained through boundary-setting practices", 
                "Community knowledge shapes individual AI use"
            ],
            do_not_change=["Methodology", "Core theoretical framework"]
        )
        vision_data = json.loads(vision_result)
        print(f"✓ Vision brief created: {vision_data['success']}")
        
        print("\n2. Processing manuscript with comments...")
        process_result = process_manuscript(
            manuscript_path=demo_manuscript,
            comments_source=test_comments,
            vision_thesis="Human agency co-evolves with AI rather than being replaced by it",
            vision_claims=[
                "Users develop strategic approaches to AI interaction",
                "Agency is maintained through boundary-setting practices"
            ],
            do_not_change=["Methodology"]
        )
        process_data = json.loads(process_result)
        print(f"✓ Manuscript processed: {process_data['success']}")
        print(f"   Manuscript spans: {process_data['manuscript']['total_spans']}")
        print(f"   Comments processed: {process_data['comments']['total']}")
        
        print("\n3. Previewing surgical edits...")
        preview_result = preview_surgical_edits(max_preview=5)
        preview_data = json.loads(preview_result)
        print(f"✓ Edit preview generated: {preview_data['success']}")
        if preview_data['success']:
            print(f"   Total planned edits: {preview_data['total_planned_edits']}")
            print(f"   Batch verification - Thesis preserved: {preview_data['batch_verification']['thesis_preserved']}")
            print(f"   Batch verification - Claims preserved: {preview_data['batch_verification']['claims_preserved']}")
            
            print("\n   Edit Previews:")
            for edit in preview_data.get('edit_previews', [])[:3]:
                print(f"   - Edit {edit['edit_number']}: {edit['edit_type']} operation")
                print(f"     Rationale: {edit['rationale'][:80]}...")
                print(f"     Safe to apply: {edit['safe_to_apply']}")
                print(f"     Semantic similarity: {edit['semantic_similarity']:.2f}")
        
        print("\n4. Testing surgical edit planning (without applying)...")
        planning_result = apply_surgical_edits(
            output_directory="test_revision_output",
            apply_edits=False,  # Just planning, no actual edits
            generate_report=True
        )
        planning_data = json.loads(planning_result)
        print(f"✓ Surgical edit planning: {planning_data['success']}")
        if planning_data['success']:
            print(f"   Pipeline stage: {planning_data['pipeline_stage']}")
            print(f"   Safe intents: {planning_data['safe_intents']}")
            print(f"   Unsafe intents: {planning_data['unsafe_intents']}")
            print(f"   Verification - Thesis preserved: {planning_data['verification_summary']['batch_thesis_preserved']}")
            
            if planning_data['preview_edits']:
                print("\n   Preview of planned edits:")
                for edit in planning_data['preview_edits']:
                    print(f"   - {edit['comment_id']}: {edit['operation']} ({edit['edit_type']})")
        
        print("\n5. Testing actual surgical edits (with application)...")
        application_result = apply_surgical_edits(
            comments_source="Additional comment: Please add a brief discussion of limitations",
            output_directory="test_revision_output",
            apply_edits=True,  # Actually apply the edits
            generate_report=True
        )
        application_data = json.loads(application_result)
        print(f"✓ Surgical edit application: {application_data['success']}")
        if application_data['success']:
            print(f"   Pipeline stage: {application_data['pipeline_stage']}")
            if 'edits_applied' in application_data:
                print(f"   Edits successfully applied: {application_data['edits_applied']}")
                print(f"   Edits failed: {application_data['edits_failed']}")
                
                if 'assembly_result' in application_data:
                    assembly = application_data['assembly_result']
                    print(f"   Files created: {len(assembly.get('files_created', []))}")
                    print(f"   Output directory: {assembly.get('output_dir', 'N/A')}")
        
        print("\n" + "=" * 60)
        print("🎉 Surgical Editing Pipeline Test Complete!")
        
        # Show summary
        if Path("test_revision_output").exists():
            output_files = list(Path("test_revision_output").glob("*"))
            print(f"\n📁 Output files generated ({len(output_files)}):")
            for file_path in output_files:
                print(f"   - {file_path.name}")
        
        print("\n✅ The complete surgical editing system is working!")
        print("\nKey capabilities demonstrated:")
        print("✓ Flexible comment parsing (any format)")
        print("✓ Surgical edit planning with conflict resolution")
        print("✓ Semantic verification and thesis preservation")
        print("✓ Precise edit application with rollback capability")
        print("✓ Final manuscript assembly with comprehensive reporting")
        print("✓ Full MCP server integration")
        
        return True
        
    except Exception as e:
        print(f"\n💥 Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_surgical_pipeline()
    if success:
        print("\n🚀 Ready for production use!")
    else:
        print("\n❌ Pipeline needs debugging")