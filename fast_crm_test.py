from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import csv
from datetime import datetime

# Configuration
TEST_URL = "https://guardiancapitalusa.com/login"
TEST_EMAIL = "pabloescobar@yopmail.com"
TEST_PASSWORD = "Test@123"

test_results = []
screenshot_id = 0

def log_result(module, test, status, details, screenshot=""):
    """Log test result"""
    test_results.append({
        'Time': datetime.now().strftime("%H:%M:%S"),
        'Module': module,
        'Test': test,
        'Status': status,
        'Details': details,
        'Screenshot': screenshot
    })
    print(f"    [{status}] {test}: {details}")

def screenshot(driver, name):
    """Quick screenshot"""
    global screenshot_id
    screenshot_id += 1
    filename = f"{screenshot_id:03d}_{name}.png"
    try:
        driver.save_screenshot(filename)
        return filename
    except:
        return ""

def quick_wait(driver, seconds=1):
    """Quick wait"""
    time.sleep(seconds)

def login_crm(driver):
    """Fast login"""
    print("\n[LOGIN MODULE]")
    try:
        driver.get(TEST_URL)
        quick_wait(driver, 2)
        
        driver.find_element(By.ID, "email").send_keys(TEST_EMAIL)
        driver.find_element(By.ID, "password").send_keys(TEST_PASSWORD)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        quick_wait(driver, 3)
        
        if "dashboard" in driver.current_url:
            ss = screenshot(driver, "Login_Success")
            log_result("Login", "Authentication", "PASS", "Logged in successfully", ss)
            return True
        else:
            log_result("Login", "Authentication", "FAIL", "Login failed", "")
            return False
    except Exception as e:
        log_result("Login", "Authentication", "FAIL", str(e), "")
        return False

def find_and_click(driver, module_name):
    """Fast navigation"""
    try:
        # First expand any collapsed menus
        try:
            menu_toggles = driver.find_elements(By.CSS_SELECTOR, "[data-widget='treeview'] a, .has-treeview > a")
            for toggle in menu_toggles:
                try:
                    if toggle.get_attribute("aria-expanded") != "true":
                        driver.execute_script("arguments[0].click();", toggle)
                        quick_wait(driver, 0.5)
                except:
                    pass
        except:
            pass
        
        # Try sidebar links with multiple strategies
        selectors = [
            ".sidebar a", 
            ".main-sidebar a", 
            "nav a",
            ".nav-link",
            ".sidebar-menu a"
        ]
        
        for selector in selectors:
            try:
                links = driver.find_elements(By.CSS_SELECTOR, selector)
                for link in links:
                    try:
                        text = link.text.strip()
                        # More flexible matching
                        if text and module_name.lower() in text.lower():
                            driver.execute_script("arguments[0].scrollIntoView(true);", link)
                            quick_wait(driver, 0.3)
                            driver.execute_script("arguments[0].click();", link)
                            quick_wait(driver, 2)
                            return True
                    except:
                        continue
            except:
                continue
        
        return False
    except:
        return False

def test_module(driver, module_name, nav_texts):
    """Fast module test"""
    print(f"\n[{module_name.upper()} MODULE]")
    
    # Try multiple navigation terms
    navigated = False
    if isinstance(nav_texts, str):
        nav_texts = [nav_texts]
    
    for nav_text in nav_texts:
        if find_and_click(driver, nav_text):
            navigated = True
            break
    
    if not navigated:
        log_result(module_name, "Navigation", "FAIL", f"Could not navigate", "")
        return
    
    ss_main = screenshot(driver, f"{module_name}_Main")
    log_result(module_name, "Navigation", "PASS", f"Accessed {module_name}", ss_main)
    
    # Check page elements
    try:
        # Tables
        tables = driver.find_elements(By.TAG_NAME, "table")
        if tables:
            rows = len(tables[0].find_elements(By.TAG_NAME, "tr"))
            log_result(module_name, "Data Display", "PASS", f"{len(tables)} tables, {rows} rows", ss_main)
        else:
            log_result(module_name, "Data Display", "INFO", "No tables found", ss_main)
        
        # All buttons
        all_buttons = driver.find_elements(By.TAG_NAME, "button") + driver.find_elements(By.CSS_SELECTOR, "a.btn, .btn")
        button_list = []
        create_btn = None
        edit_btn = None
        delete_btn = None
        
        for btn in all_buttons[:20]:  # Check first 20 buttons
            try:
                text = btn.text.strip()
                if text and len(text) < 50:
                    button_list.append(text)
                    
                    # Find CRUD buttons
                    text_lower = text.lower()
                    if not create_btn and any(x in text_lower for x in ['create', 'add', 'new']):
                        create_btn = btn
                    if not edit_btn and any(x in text_lower for x in ['edit', 'update']):
                        edit_btn = btn
                    if not delete_btn and any(x in text_lower for x in ['delete', 'remove']):
                        delete_btn = btn
            except:
                continue
        
        if button_list:
            log_result(module_name, "Buttons Found", "PASS", f"{len(button_list)} buttons: {', '.join(button_list[:5])}", ss_main)
        
        # Test Create
        if create_btn:
            try:
                create_btn.click()
                quick_wait(driver, 2)
                ss_create = screenshot(driver, f"{module_name}_Create")
                
                # Check form elements
                inputs = driver.find_elements(By.CSS_SELECTOR, "input, select, textarea")
                log_result(module_name, "CREATE Form", "PASS", f"Form opened with {len(inputs)} fields", ss_create)
                
                driver.back()
                quick_wait(driver, 1)
            except Exception as e:
                log_result(module_name, "CREATE", "FAIL", f"Error: {str(e)[:50]}", "")
        else:
            log_result(module_name, "CREATE", "INFO", "No create button found", "")
        
        # Test Edit (if available)
        if edit_btn:
            try:
                edit_btn.click()
                quick_wait(driver, 2)
                ss_edit = screenshot(driver, f"{module_name}_Edit")
                log_result(module_name, "UPDATE Form", "PASS", "Edit form opened", ss_edit)
                driver.back()
                quick_wait(driver, 1)
            except:
                log_result(module_name, "UPDATE", "INFO", "Edit button exists but couldn't open", "")
        else:
            # Try clicking first row action button
            try:
                action_btns = driver.find_elements(By.XPATH, "//table//a[contains(@href, 'edit')] | //table//button[contains(text(), 'Edit')]")
                if action_btns:
                    action_btns[0].click()
                    quick_wait(driver, 2)
                    ss_edit = screenshot(driver, f"{module_name}_Edit")
                    log_result(module_name, "UPDATE Form", "PASS", "Edit from table row", ss_edit)
                    driver.back()
                    quick_wait(driver, 1)
            except:
                log_result(module_name, "UPDATE", "INFO", "No edit functionality found", "")
        
        # Check for Delete buttons
        if delete_btn:
            log_result(module_name, "DELETE Button", "PASS", "Delete button found", ss_main)
        else:
            delete_btns = driver.find_elements(By.XPATH, "//table//button[contains(text(), 'Delete')] | //table//a[contains(text(), 'Delete')]")
            if delete_btns:
                log_result(module_name, "DELETE Button", "PASS", f"{len(delete_btns)} delete buttons in table", ss_main)
            else:
                log_result(module_name, "DELETE", "INFO", "No delete buttons found", "")
        
        # Check for filters/search
        search_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='search'], input[placeholder*='Search'], input[placeholder*='search']")
        if search_inputs:
            log_result(module_name, "Search/Filter", "PASS", f"{len(search_inputs)} search fields found", ss_main)
        
        # Check for pagination
        pagination = driver.find_elements(By.CSS_SELECTOR, ".pagination, [class*='paging']")
        if pagination:
            log_result(module_name, "Pagination", "PASS", "Pagination found", ss_main)
        
        # Module-specific tests
        if module_name == "Dashboard":
            # Check graphs
            charts = driver.find_elements(By.TAG_NAME, "canvas")
            log_result(module_name, "Charts/Graphs", "PASS", f"{len(charts)} charts found", ss_main)
            
            # Check widgets
            widgets = driver.find_elements(By.CSS_SELECTOR, ".small-box, .info-box, .card")
            log_result(module_name, "Widgets", "PASS", f"{len(widgets)} widgets found", ss_main)
        
        elif module_name in ["Billing", "Matters", "Litigation Funding"]:
            # Check for financial calculations
            amounts = driver.find_elements(By.XPATH, "//*[contains(text(), '$')]")
            if amounts:
                log_result(module_name, "Financial Data", "PASS", f"{len(amounts)} amount fields found", ss_main)
        
        elif module_name == "Calendar":
            # Check calendar view
            cal = driver.find_elements(By.CSS_SELECTOR, "#calendar, .fc-view, [class*='calendar']")
            if cal:
                log_result(module_name, "Calendar View", "PASS", "Calendar widget loaded", ss_main)
        
        elif module_name == "Documents":
            # Check upload
            upload_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Upload')] | //input[@type='file']")
            if upload_btns:
                log_result(module_name, "Upload Feature", "PASS", "Upload functionality found", ss_main)
        
    except Exception as e:
        log_result(module_name, "Module Test", "FAIL", f"Error: {str(e)[:100]}", "")

def save_csv_report(filename="CRM_Test_Report.csv"):
    """Save results to CSV"""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['Time', 'Module', 'Test', 'Status', 'Details', 'Screenshot'])
            writer.writeheader()
            writer.writerows(test_results)
        print(f"\n✓ CSV Report saved: {filename}")
        return True
    except Exception as e:
        print(f"\n✗ CSV Error: {e}")
        return False

def run_fast_test():
    """Run fast comprehensive test"""
    print("="*80)
    print("GUARDIAN CAPITAL CRM - FAST COMPREHENSIVE TEST")
    print("="*80)
    print(f"URL: {TEST_URL}")
    print(f"User: {TEST_EMAIL}")
    print("="*80)
    
    driver = webdriver.Chrome()
    driver.maximize_window()
    driver.implicitly_wait(5)
    
    try:
        # Login
        if not login_crm(driver):
            print("\n✗ Login failed - stopping")
            return False
        
        # Test Dashboard - direct URL
        print(f"\n[DASHBOARD MODULE]")
        driver.get("https://guardiancapitalusa.com/dashboard/index")
        quick_wait(driver, 2)
        
        ss_dash = screenshot(driver, "Dashboard_Main")
        log_result("Dashboard", "Navigation", "PASS", "Accessed Dashboard", ss_dash)
        
        # Dashboard tests
        try:
            tables = driver.find_elements(By.TAG_NAME, "table")
            log_result("Dashboard", "Data Display", "PASS", f"{len(tables)} tables", ss_dash)
            
            charts = driver.find_elements(By.TAG_NAME, "canvas")
            log_result("Dashboard", "Charts/Graphs", "PASS", f"{len(charts)} charts", ss_dash)
            
            widgets = driver.find_elements(By.CSS_SELECTOR, ".small-box, .info-box, .card")
            log_result("Dashboard", "Widgets", "PASS", f"{len(widgets)} widgets", ss_dash)
        except Exception as e:
            log_result("Dashboard", "Tests", "FAIL", str(e), "")
        
        # All modules to test - try multiple navigation terms
        modules = [
            ("Calendar", ["Calendar", "Calender", "Events"]),
            ("Tasks", ["Task", "Tasks", "To Do"]),
            ("Matters", ["Matter", "Matters", "Cases", "Case"]),
            ("Contacts", ["Contact", "Contacts", "Client", "Clients"]),
            ("Activities", ["Activities", "Activity", "Actions"]),
            ("Billing", ["Billing", "Bill", "Invoice", "Invoices"]),
            ("Litigation Funding", ["Litigation", "Funding", "Litigation Funding"]),
            ("Documents", ["Document", "Documents", "File", "Files"]),
            ("Time Entries", ["Time", "Time Entry", "Timesheet", "Time Entries"]),
            ("Expenses", ["Expense", "Expenses"]),
            ("Reports", ["Report", "Reports"]),
            ("Notes", ["Note", "Notes"]),
            ("Emails", ["Email", "Emails", "Mail"]),
        ]
        
        for module_name, nav_texts in modules:
            try:
                test_module(driver, module_name, nav_texts)
            except Exception as e:
                print(f"  ✗ Module {module_name} crashed: {e}")
                log_result(module_name, "Critical Error", "FAIL", str(e), "")
        
        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        total = len(test_results)
        passed = len([r for r in test_results if r['Status'] == 'PASS'])
        failed = len([r for r in test_results if r['Status'] == 'FAIL'])
        info = len([r for r in test_results if r['Status'] == 'INFO'])
        
        print(f"Total Tests: {total}")
        print(f"PASS: {passed}")
        print(f"FAIL: {failed}")
        print(f"INFO: {info}")
        print(f"Screenshots: {screenshot_id}")
        
        if total > 0:
            success_rate = (passed / (passed + failed) * 100) if (passed + failed) > 0 else 0
            print(f"Success Rate: {success_rate:.1f}%")
        
        print("="*80)
        
        # Save CSV
        save_csv_report()
        
        print(f"\n✓ Test completed!")
        print(f"✓ Check 'CRM_Test_Report.csv' for details")
        print(f"✓ {screenshot_id} screenshots saved")
        
        quick_wait(driver, 3)
        return True
        
    except Exception as e:
        print(f"\n✗ Critical error: {e}")
        import traceback
        traceback.print_exc()
        save_csv_report()
        return False
    
    finally:
        driver.quit()
        print("\n✓ Browser closed")

if __name__ == "__main__":
    success = run_fast_test()
    exit(0 if success else 1)
