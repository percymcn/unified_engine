#!/usr/bin/env python3
"""
Test runner script for the Unified Trading Engine.
Runs all test suites and generates comprehensive test reports.
"""

import os
import sys
import subprocess
import time
from datetime import datetime
import json


class TestRunner:
    """Comprehensive test runner for all test suites."""
    
    def __init__(self):
        self.test_dir = os.path.dirname(os.path.abspath(__file__))
        self.results = {}
        self.start_time = datetime.now()
    
    def run_test_suite(self, test_file, suite_name):
        """Run a specific test suite."""
        print(f"\n{'='*60}")
        print(f"Running {suite_name}")
        print(f"{'='*60}")
        
        test_path = os.path.join(self.test_dir, test_file)
        
        if not os.path.exists(test_path):
            print(f"❌ Test file not found: {test_path}")
            return False
        
        try:
            # Run pytest with coverage and verbose output
            cmd = [
                sys.executable, "-m", "pytest", 
                test_path,
                "-v",
                "--tb=short",
                "--no-header",
                "--color=yes"
            ]
            
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)
            end_time = time.time()
            
            duration = end_time - start_time
            
            # Parse results
            output = result.stdout + result.stderr
            success = result.returncode == 0
            
            # Extract test statistics
            passed = output.count("PASSED")
            failed = output.count("FAILED")
            errors = output.count("ERROR")
            skipped = output.count("SKIPPED")
            
            self.results[suite_name] = {
                "success": success,
                "failed": failed,
                "errors": errors,
                "skipped": skipped,
                "duration": duration,
                "output": output,
                "return_code": result.returncode
            }
            
            # Print summary
            if success:
                print(f"✅ {suite_name} PASSED")
            else:
                print(f"❌ {suite_name} FAILED")
            
            print(f"   Passed: {passed}, Failed: {failed}, Errors: {errors}, Skipped: {skipped}")
            print(f"   Duration: {duration:.2f}s")
            
            if not success:
                print(f"\n--- Error Output ---")
                print(output[-1000:])  # Last 1000 chars of output
            
            return success
            
        except Exception as e:
            print(f"❌ Error running {suite_name}: {e}")
            self.results[suite_name] = {
                "success": False,
                "error": str(e),
                "duration": 0
            }
            return False
    
    def run_all_tests(self):
        """Run all test suites."""
        test_suites = [
            ("test_brokers.py", "Broker Executors"),
            ("test_webhooks.py", "Webhook Processing"),
            ("test_api.py", "API Endpoints"),
            ("test_websockets.py", "WebSocket Connections"),
            ("test_e2e.py", "End-to-End Workflows"),
            ("test_ui_integration.py", "UI Integration"),
            ("test_deployment.py", "Deployment & Health"),
            ("test_performance.py", "Performance & Load")
        ]
        
        print("🚀 Starting Unified Trading Engine Test Suite")
        print(f"📅 Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Test directory: {self.test_dir}")
        
        overall_success = True
        
        for test_file, suite_name in test_suites:
            success = self.run_test_suite(test_file, suite_name)
            if not success:
                overall_success = False
        
        return overall_success
    
    def generate_report(self):
        """Generate comprehensive test report."""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        print(f"\n{'='*80}")
        print("📊 COMPREHENSIVE TEST REPORT")
        print(f"{'='*80}")
        print(f"📅 Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Total duration: {total_duration:.2f}s")
        
        # Calculate totals
        total_passed = sum(r.get("success", 0) for r in self.results.values() if isinstance(r, dict))
        total_failed = sum(r.get("failed", 0) for r in self.results.values() if isinstance(r, dict))
        total_errors = sum(r.get("errors", 0) for r in self.results.values() if isinstance(r, dict))
        total_skipped = sum(r.get("skipped", 0) for r in self.results.values() if isinstance(r, dict))
        
        print(f"\n📈 SUMMARY:")
        print(f"   Total Passed: {total_passed}")
        print(f"   Total Failed: {total_failed}")
        print(f"   Total Errors: {total_errors}")
        print(f"   Total Skipped: {total_skipped}")
        
        # Suite breakdown
        print(f"\n📋 SUITE BREAKDOWN:")
        for suite_name, results in self.results.items():
            if isinstance(results, dict) and "success" in results:
                status = "✅ PASS" if results["success"] else "❌ FAIL"
                duration = results.get("duration", 0)
                print(f"   {suite_name:25} {status:8} {duration:6.2f}s")
            elif "error" in results:
                print(f"   {suite_name:25} ❌ ERROR  -")
        
        # Save detailed report
        report_data = {
            "timestamp": self.start_time.isoformat(),
            "duration": total_duration,
            "summary": {
                "passed": total_passed,
                "failed": total_failed,
                "errors": total_errors,
                "skipped": total_skipped
            },
            "suites": self.results
        }
        
        report_file = os.path.join(self.test_dir, "test_report.json")
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\n💾 Detailed report saved to: {report_file}")
        
        # Overall result
        if total_failed == 0 and total_errors == 0:
            print(f"\n🎉 ALL TESTS PASSED! 🎉")
            return True
        else:
            print(f"\n⚠️  SOME TESTS FAILED")
            return False
    
    def run_coverage(self):
        """Run test coverage analysis."""
        print(f"\n{'='*60}")
        print("📊 Running Coverage Analysis")
        print(f"{'='*60}")
        
        try:
            cmd = [
                sys.executable, "-m", "pytest",
                "--cov=app",
                "--cov-report=term-missing",
                "--cov-report=html",
                "--cov-report=json",
                "test_*.py"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_dir)
            
            if result.returncode == 0:
                print("✅ Coverage analysis completed")
                print("📄 HTML coverage report generated in htmlcov/")
                print("📄 JSON coverage report saved to coverage.json")
            else:
                print("❌ Coverage analysis failed")
                print(result.stderr)
                
        except Exception as e:
            print(f"❌ Error running coverage: {e}")


def main():
    """Main test runner entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Unified Trading Engine Test Runner")
    parser.add_argument("--coverage", action="store_true", help="Run coverage analysis")
    parser.add_argument("--suite", help="Run specific test suite (e.g., test_brokers.py)")
    parser.add_argument("--report-only", action="store_true", help="Only generate report from existing results")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.report_only:
        runner.generate_report()
        return
    
    if args.suite:
        # Run specific test suite
        suite_name = args.suite.replace(".py", "").replace("test_", "").replace("_", " ").title()
        success = runner.run_test_suite(args.suite, suite_name)
    else:
        # Run all tests
        success = runner.run_all_tests()
    
    # Generate report
    report_success = runner.generate_report()
    
    # Run coverage if requested
    if args.coverage:
        runner.run_coverage()
    
    # Exit with appropriate code
    sys.exit(0 if success and report_success else 1)


if __name__ == "__main__":
    main()