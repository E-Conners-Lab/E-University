#!/usr/bin/env python3
"""
Network Automation Orchestrator
===============================
Main pipeline script that coordinates the full deployment workflow:

1. Generate configs from templates
2. Run pre-deployment validation
3. Deploy configs with diff preview
4. Run post-deployment validation
5. Report results

Usage:
    python orchestrate.py --plan              # Show what would happen
    python orchestrate.py --execute           # Run full pipeline
    python orchestrate.py --generate-only     # Just generate configs
    python orchestrate.py --validate-only     # Just run validation
"""

import argparse
import sys
import subprocess
from datetime import datetime
from pathlib import Path


class PipelineOrchestrator:
    """Orchestrates the full deployment pipeline."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.scripts_dir = self.base_dir / "scripts"
        self.results = {
            "generate": None,
            "pre_validate": None,
            "deploy": None,
            "post_validate": None,
        }
    
    def print_header(self, title: str):
        """Print a formatted header."""
        print()
        print("╔" + "═" * 68 + "╗")
        print(f"║  {title:64}  ║")
        print("╚" + "═" * 68 + "╝")
        print()
    
    def run_step(self, name: str, script: str, args: list = None) -> bool:
        """Run a pipeline step."""
        args = args or []
        cmd = [sys.executable, str(self.scripts_dir / script)] + args
        
        print(f"Running: {' '.join(cmd)}")
        print("-" * 60)
        
        result = subprocess.run(cmd, cwd=str(self.base_dir))
        
        self.results[name] = result.returncode == 0
        return result.returncode == 0
    
    def show_plan(self):
        """Show what the pipeline would do."""
        self.print_header("DEPLOYMENT PLAN")
        
        print("""
This pipeline will execute the following steps:

┌─────────────────────────────────────────────────────────────────────┐
│  STEP 1: Generate Configurations                                   │
├─────────────────────────────────────────────────────────────────────┤
│  • Read intent data (device definitions)                           │
│  • Render Jinja2 templates                                         │
│  • Save configs to configs/generated/                              │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 2: Pre-Deployment Validation                                 │
├─────────────────────────────────────────────────────────────────────┤
│  • Test SSH connectivity to all devices                            │
│  • Verify interfaces are up                                        │
│  • Ensure network is healthy before changes                        │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 3: Deploy Configurations                                     │
├─────────────────────────────────────────────────────────────────────┤
│  • Show diff of changes (what will be modified)                    │
│  • Backup current running configs                                  │
│  • Apply new configs in staged rollout                             │
│  • Save configs to startup                                         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 4: Post-Deployment Validation                                │
├─────────────────────────────────────────────────────────────────────┤
│  • Verify SSH connectivity                                         │
│  • Check OSPF neighbors are FULL                                   │
│  • Check BGP sessions are Established                              │
│  • Verify MPLS LDP neighbors                                       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 5: Report Results                                            │
├─────────────────────────────────────────────────────────────────────┤
│  • Summary of all steps                                            │
│  • Pass/Fail status                                                │
│  • Rollback instructions if needed                                 │
└─────────────────────────────────────────────────────────────────────┘
""")
    
    def execute_pipeline(self, skip_deploy: bool = False):
        """Execute the full pipeline."""
        start_time = datetime.now()
        
        self.print_header("NETWORK AUTOMATION PIPELINE")
        print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Base Dir: {self.base_dir}")
        
        # Step 1: Generate Configs
        self.print_header("STEP 1: GENERATE CONFIGURATIONS")
        if not self.run_step("generate", "generate_configs.py"):
            print("\n❌ Config generation failed! Aborting pipeline.")
            return False
        
        # Step 2: Pre-Validation
        self.print_header("STEP 2: PRE-DEPLOYMENT VALIDATION")
        if not self.run_step("pre_validate", "validate.py", ["--pre"]):
            print("\n⚠️  Pre-validation found issues!")
            proceed = input("Continue anyway? (yes/no): ")
            if proceed.lower() != "yes":
                print("Pipeline aborted.")
                return False
        
        # Step 3: Deploy
        if not skip_deploy:
            self.print_header("STEP 3: DEPLOY CONFIGURATIONS")
            
            # First show diff
            print("Showing configuration diff...\n")
            self.run_step("diff", "deploy.py", ["--diff"])
            
            print("\n" + "=" * 60)
            proceed = input("\nProceed with deployment? (yes/no): ")
            if proceed.lower() != "yes":
                print("Deployment skipped.")
                self.results["deploy"] = None
            else:
                if not self.run_step("deploy", "deploy.py", ["--deploy"]):
                    print("\n❌ Deployment failed!")
                    print("Check errors above and consider rollback.")
                    return False
        else:
            print("\n[Skipping deployment - dry run mode]")
        
        # Step 4: Post-Validation
        if self.results.get("deploy"):
            self.print_header("STEP 4: POST-DEPLOYMENT VALIDATION")
            if not self.run_step("post_validate", "validate.py", ["--post"]):
                print("\n⚠️  Post-validation found issues!")
                print("Review the failures and consider rollback if needed.")
        
        # Step 5: Summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        self.print_header("PIPELINE SUMMARY")
        
        print(f"Duration: {duration}")
        print()
        print("Step Results:")
        print(f"  1. Generate Configs:    {'✓ PASS' if self.results.get('generate') else '✗ FAIL'}")
        print(f"  2. Pre-Validation:      {'✓ PASS' if self.results.get('pre_validate') else '✗ FAIL'}")
        
        deploy_status = self.results.get('deploy')
        if deploy_status is None:
            print(f"  3. Deploy:              - SKIPPED")
        else:
            print(f"  3. Deploy:              {'✓ PASS' if deploy_status else '✗ FAIL'}")
        
        post_status = self.results.get('post_validate')
        if post_status is None:
            print(f"  4. Post-Validation:     - SKIPPED")
        else:
            print(f"  4. Post-Validation:     {'✓ PASS' if post_status else '✗ FAIL'}")
        
        print()
        
        # Overall result
        all_passed = all(
            v is True or v is None 
            for v in self.results.values()
        )
        
        if all_passed:
            print("═" * 60)
            print("  ✓ PIPELINE COMPLETED SUCCESSFULLY")
            print("═" * 60)
        else:
            print("═" * 60)
            print("  ✗ PIPELINE COMPLETED WITH ERRORS")
            print("═" * 60)
            print("\nTo rollback a device:")
            print("  python scripts/deploy.py --rollback DEVICE_NAME")
        
        print()
        return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="Network Automation Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python orchestrate.py --plan              Show what would happen
  python orchestrate.py --execute           Run full pipeline
  python orchestrate.py --generate-only     Just generate configs
  python orchestrate.py --validate-only     Just run validation
        """
    )
    parser.add_argument("--plan", action="store_true", help="Show deployment plan")
    parser.add_argument("--execute", action="store_true", help="Execute full pipeline")
    parser.add_argument("--generate-only", action="store_true", help="Only generate configs")
    parser.add_argument("--validate-only", action="store_true", help="Only run validation")
    parser.add_argument("--dry-run", action="store_true", help="Run pipeline without deploying")
    
    args = parser.parse_args()
    
    orchestrator = PipelineOrchestrator()
    
    if args.plan:
        orchestrator.show_plan()
    elif args.generate_only:
        orchestrator.run_step("generate", "generate_configs.py")
    elif args.validate_only:
        orchestrator.run_step("validate", "validate.py", ["--pre"])
    elif args.execute:
        success = orchestrator.execute_pipeline(skip_deploy=args.dry_run)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
