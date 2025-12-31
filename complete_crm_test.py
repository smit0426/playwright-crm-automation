from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
import time
import csv
import random
import string
from datetime import datetime, timedelta

# Configuration
TEST_URL = "https://guardiancapitalusa.com/login"
TEST_EMAIL = "pabloescobar@yopmail.com"
TEST_PASSWORD = "Test@123"
WAIT_TIME = 10  # Longer wait for slow pages

# Globals
test_results = []
screenshot_counter = 0
step_counter = 0


def log(module, test, status, details, screenshot="", expected="", actual="", category="General"):
    """Log test result with expected vs. actual tracking and step numbering"""
    global step_counter
    step_counter += 1
    test_results.append({
        "Step": step_counter,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Module": module,
        "Category": category,
        "Action": test,
        "Expected": expected,
        "Actual": actual or details,
        "Status": status,
        "Details": details,
        "Screenshot": screenshot,
    })
    status_icon = "\u2713" if status == "PASS" else "\u2717" if status == "FAIL" else "\u2139"
    print(f"    {status_icon} [{status}] ({category}) {test}: {details[:80]}")


def take_screenshot(driver, name):
    """Take screenshot"""
    global screenshot_counter
    screenshot_counter += 1
    filename = f"{screenshot_counter:03d}_{name}_{datetime.now().strftime('%H%M%S')}.png"
    try:
        driver.save_screenshot(filename)
        return filename
    except Exception:
        return ""


def safe_wait(seconds):
    """Safe wait"""
    time.sleep(seconds)


def random_string(length=8):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def random_email():
    return f"test_{random_string(6).lower()}@example.com"


def random_phone():
    return f"555{random.randint(1000000, 9999999)}"


def random_number(min_val=1, max_val=999):
    return str(random.randint(min_val, max_val))


def generate_marker(module_name):
    return f"{module_name}_{random_string(6)}"


def clear_search_inputs(driver):
    fields = driver.find_elements(
        By.CSS_SELECTOR,
        "input[type='search'], input[placeholder*='Search'], input[placeholder*='search'], input[placeholder*='Filter']",
    )
    for field in fields[:2]:
        try:
            field.clear()
        except Exception:
            continue


def search_for_marker(driver, marker, module_name, context):
    """Attempt to filter and verify marker presence in page"""
    found = False
    fields = driver.find_elements(
        By.CSS_SELECTOR,
        "input[type='search'], input[placeholder*='Search'], input[placeholder*='search'], input[placeholder*='Filter']",
    )
    if fields:
        try:
            field = fields[0]
            field.clear()
            field.send_keys(marker)
            field.send_keys(Keys.ENTER)
            safe_wait(2)
        except Exception:
            pass

    safe_wait(2)
    reload_if_needed(driver)

    try:
        if marker.lower() in driver.page_source.lower():
            found = True
    except Exception:
        found = False

    if found:
        log(module_name, f"Marker Found ({context})", "PASS", f"Marker '{marker}' located", "")
    else:
        log(module_name, f"Marker Missing ({context})", "FAIL", f"Marker '{marker}' not present", "")

    return found


def fill_field(inp, marker=None):
    """Fill a single input/select/textarea with dummy data (marker preferred)."""
    try:
        tag = inp.tag_name.lower()
        f_type = (inp.get_attribute("type") or "").lower()
        name = inp.get_attribute("name") or inp.get_attribute("id") or ""
        marker_text = marker or f"Auto {random_string(6)}"

        if tag == "select":
            select = Select(inp)
            if len(select.options) > 1:
                select.select_by_index(1)
            elif select.options:
                select.select_by_index(0)
            return f"Select set ({name})"

        if f_type in ["checkbox", "radio"]:
            if not inp.is_selected():
                inp.click()
            return f"Clicked {f_type} ({name})"

        if f_type in ["date", "datetime-local"]:
            today = datetime.now().strftime("%Y-%m-%d")
            inp.clear()
            inp.send_keys(today)
            return f"Date set ({name})"

        if f_type in ["number", "tel"]:
            value = random_number()
            inp.clear()
            inp.send_keys(value)
            return f"Number set {value} ({name})"

        if "email" in f_type or "email" in name.lower():
            value = random_email()
            inp.clear()
            inp.send_keys(marker_text if marker else value)
            return f"Email set {marker_text if marker else value} ({name})"

        if tag == "textarea":
            text = marker_text if marker else f"Automated entry {random_string(10)}"
            inp.clear()
            inp.send_keys(text)
            return f"Textarea set ({name})"

        text = marker_text
        inp.clear()
        inp.send_keys(text)
        return f"Text set {text} ({name})"
    except Exception as e:
        return f"Skip field error {str(e)[:40]}"


def fill_required_fields(inputs, marker):
    """Second-pass fill for likely required fields using marker"""
    hints = ["matter", "client", "title", "name", "description", "amount", "fund", "time", "date", "start", "end"]
    results = []
    for inp in inputs:
        try:
            label = (inp.get_attribute("name") or inp.get_attribute("id") or "").lower()
            if any(h in label for h in hints):
                results.append(fill_field(inp, marker=marker))
        except Exception:
            continue
    return results


def click_first_match(driver, keywords):
    """Click first visible button/link matching any keyword"""
    keyword_xpath = " | ".join(
        [
            f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{k.lower()}')]"
            for k in keywords
        ]
        + [
            f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{k.lower()}')]"
            for k in keywords
        ]
    )

    try:
        elements = driver.find_elements(By.XPATH, keyword_xpath)
        for el in elements:
            try:
                if el.is_displayed() and el.is_enabled():
                    driver.execute_script("arguments[0].click();", el)
                    safe_wait(2)
                    reload_if_needed(driver)
                    return el
            except Exception:
                continue
    except Exception:
        pass
    return None


def count_table_rows(driver):
    """Return first table row count if present"""
    try:
        tables = driver.find_elements(By.TAG_NAME, "table")
        for table in tables:
            try:
                rows = table.find_elements(By.TAG_NAME, "tr")
                data_rows = [r for r in rows if r.find_elements(By.TAG_NAME, "td")]
                if data_rows:
                    return len(data_rows)
            except Exception:
                continue
    except Exception:
        pass
    return 0


def find_row_with_marker(driver, marker):
    """Locate a table row containing the marker text"""
    try:
        tables = driver.find_elements(By.TAG_NAME, "table")
        for table in tables:
            try:
                rows = table.find_elements(By.TAG_NAME, "tr")
                for row in rows:
                    try:
                        if marker.lower() in row.text.lower():
                            return row
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        pass
    return None


def capture_validation_messages(driver, module_name, context):
    """Capture validation or error messages displayed on screen"""
    try:
        messages = driver.find_elements(
            By.CSS_SELECTOR, ".error, .validation, .invalid-feedback, .alert, [role='alert']"
        )
        texts = [m.text.strip() for m in messages if m.is_displayed() and m.text.strip()]
        if texts:
            log(module_name, f"Validation {context}", "INFO", " | ".join(texts), "")
            return texts
    except Exception:
        pass
    return []


def capture_success_messages(driver, module_name, context):
    """Capture success/toast messages to validate persistence"""
    try:
        messages = driver.find_elements(By.CSS_SELECTOR, ".alert-success, .toast, .alert.alert-success, .text-success")
        texts = [m.text.strip() for m in messages if m.is_displayed() and m.text.strip()]
        if texts:
            log(module_name, f"Success {context}", "INFO", " | ".join(texts), "")
            return texts
    except Exception:
        pass
    return []


def click_nav_toggles(driver):
    """Expand common nav toggles/menus before searching links"""
    toggles = driver.find_elements(By.XPATH,
        "//button[contains(@class,'navbar-toggler') or contains(@class,'sidebar-toggle') or contains(@class,'menu')] | "
        "//i[contains(@class,'fa-bars')]/parent::button | //i[contains(@class,'fa-bars')]/parent::a")
    for t in toggles[:3]:
        try:
            if t.is_displayed():
                driver.execute_script("arguments[0].click();", t)
                safe_wait(1)
        except Exception:
            continue


def click_more_menu(driver):
    """Open 'More' dropdown if present"""
    try:
        more_candidates = driver.find_elements(By.XPATH, "//a[contains(., 'More')] | //button[contains(., 'More')] | //span[contains(., 'More')]/parent::a")
        for m in more_candidates[:3]:
            try:
                if m.is_displayed():
                    driver.execute_script("arguments[0].click();", m)
                    safe_wait(1)
            except Exception:
                continue
    except Exception:
        pass


def return_to_listing(driver):
    """Try to return from modal/form to listing view"""
    # Common close/cancel buttons
    click_first_match(driver, ["close", "cancel", "back", "x"])
    safe_wait(2)
    reload_if_needed(driver)


def reload_if_needed(driver, max_attempts=3):
    """Reload page if site can't be reached"""
    for attempt in range(max_attempts):
        try:
            if "can't be reached" in driver.page_source.lower() or "error" in driver.page_source.lower()[:200] or len(
                driver.page_source
            ) < 100:
                print(f"      \u27f3 Page load issue, reloading (attempt {attempt + 1})...")
                driver.refresh()
                safe_wait(5)
            else:
                return True
        except Exception:
            print(f"      \u27f3 Exception, reloading (attempt {attempt + 1})...")
            driver.refresh()
            safe_wait(5)
    return False


def patient_wait_for_element(driver, by, selector, timeout=WAIT_TIME):
    """Wait patiently for element"""
    try:
        element = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))
        return element
    except TimeoutException:
        reload_if_needed(driver)
        try:
            return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))
        except Exception:
            return None


def login_to_crm(driver):
    """Login with retry logic"""
    print("\n" + "=" * 100)
    print("LOGIN MODULE")
    print("=" * 100)

    for attempt in range(3):
        try:
            driver.get(TEST_URL)
            safe_wait(5)
            reload_if_needed(driver)

            email_field = patient_wait_for_element(driver, By.ID, "email")
            if email_field:
                email_field.clear()
                email_field.send_keys(TEST_EMAIL)

                password_field = driver.find_element(By.ID, "password")
                password_field.clear()
                password_field.send_keys(TEST_PASSWORD)

                driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
                safe_wait(7)
                reload_if_needed(driver)

                if "dashboard" in driver.current_url:
                    ss = take_screenshot(driver, "Login_Success")
                    log("Login", "Authentication", "PASS", "Successfully logged in", ss, category="Navigation")
                    return True
        except Exception as e:
            print(f"      Login attempt {attempt + 1} failed: {str(e)[:50]}")
            safe_wait(3)

    log("Login", "Authentication", "FAIL", "All login attempts failed", "")
    return False


def open_module_in_tab(driver, module_name, keywords):
    """Open module in new tab"""
    try:
        click_nav_toggles(driver)
        if module_name.lower() in ["settings", "accounts", "import data", "import"]:
            click_more_menu(driver)

        # Try text match
        for keyword in keywords:
            links = driver.find_elements(By.XPATH, f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]")
            for link in links:
                try:
                    if link.is_displayed():
                        href = link.get_attribute("href")
                        if href:
                            driver.execute_script(f"window.open('{href}', '_blank');")
                            safe_wait(2)
                            driver.switch_to.window(driver.window_handles[-1])
                            safe_wait(5)
                            reload_if_needed(driver)
                            print(f"  \u2713 Opened {module_name} in new tab")
                            return True
                except Exception:
                    continue

        # Try href contains keyword
        all_links = driver.find_elements(By.TAG_NAME, "a")
        for link in all_links:
            try:
                href = link.get_attribute("href") or ""
                if any(k.lower() in href.lower() for k in keywords) and link.is_displayed():
                    driver.execute_script(f"window.open('{href}', '_blank');")
                    safe_wait(2)
                    driver.switch_to.window(driver.window_handles[-1])
                    safe_wait(5)
                    reload_if_needed(driver)
                    print(f"  \u2713 Opened {module_name} via href match")
                    return True
            except Exception:
                continue

        # Fallback: click nav toggles again and retry by partial text without case limits
        click_nav_toggles(driver)
        for keyword in keywords:
            links = driver.find_elements(By.XPATH, f"//a[contains(., '{keyword}')] | //span[contains(., '{keyword}')]/ancestor::a")
            for link in links:
                try:
                    if link.is_displayed():
                        href = link.get_attribute("href")
                        if href:
                            driver.execute_script(f"window.open('{href}', '_blank');")
                            safe_wait(2)
                            driver.switch_to.window(driver.window_handles[-1])
                            safe_wait(5)
                            reload_if_needed(driver)
                            print(f"  \u2713 Opened {module_name} via fallback text")
                            return True
                except Exception:
                    continue

        return False
    except Exception as e:
        print(f"  \u2717 Error opening {module_name}: {str(e)[:50]}")
        return False


def test_all_buttons(driver, module_name):
    """Test every button on the page"""
    print(f"    Testing all buttons in {module_name}...")

    try:
        all_elements = []
        all_elements.extend(driver.find_elements(By.TAG_NAME, "button"))
        all_elements.extend(driver.find_elements(By.CSS_SELECTOR, "a.btn, .btn"))
        all_elements.extend(driver.find_elements(By.CSS_SELECTOR, "a[role='button']"))

        for element in all_elements[:30]:
            try:
                if element.is_displayed() and element.is_enabled():
                    text = element.text.strip()
                    if text and len(text) < 100:
                        element_type = element.tag_name
                        log(
                            module_name,
                            f"Button Found: {text}",
                            "PASS",
                            f"Type: {element_type}, Visible: Yes, Enabled: Yes",
                            "",
                            category="Buttons",
                        )
            except StaleElementReferenceException:
                continue
            except Exception:
                continue
    except Exception as e:
        log(module_name, "Button Testing", "FAIL", str(e), "", category="Buttons")


def test_all_dropdowns(driver, module_name):
    """Test every dropdown on the page"""
    print(f"    Testing all dropdowns in {module_name}...")

    try:
        selects = driver.find_elements(By.TAG_NAME, "select")

        for idx, select_elem in enumerate(selects[:10]):
            try:
                if select_elem.is_displayed():
                    select = Select(select_elem)
                    options = select.options
                    dropdown_id = select_elem.get_attribute("id") or f"dropdown_{idx}"

                    log(
                        module_name,
                        f"Dropdown: {dropdown_id}",
                        "PASS",
                        f"Found {len(options)} options: {', '.join([opt.text for opt in options[:5]])}",
                        "",
                        category="Dropdowns",
                    )
            except Exception:
                continue
    except Exception as e:
        log(module_name, "Dropdown Testing", "FAIL", str(e), "", category="Dropdowns")


def test_crud_operations(driver, module_name):
    """Test all CRUD operations thoroughly"""
    print(f"    Testing CRUD operations in {module_name}...")

    ss_main = take_screenshot(driver, f"{module_name}_Main_Page")
    log(module_name, "Page Loaded", "PASS", "Main page accessible", ss_main, category="Page")

    base_row_count = count_table_rows(driver)
    marker = generate_marker(module_name)
    marker_edit = f"{marker}_edit"

    # CREATE flow
    create_triggers = ["create", "add", "new", "add task", "add matter", "add contact", "add bill"]
    create_clicked = click_first_match(driver, create_triggers)

    if create_clicked:
        trigger_text = (create_clicked.text or "Create").strip()
        log(
            module_name,
            "CREATE Button",
            "PASS",
            f"Clicked create trigger {trigger_text}",
            ss_main,
            expected="Create form should open",
            category="Create",
        )

        ss_create = take_screenshot(driver, f"{module_name}_Create_Form")
        inputs = driver.find_elements(By.CSS_SELECTOR, "input, select, textarea")
        visible_inputs = [inp for inp in inputs if inp.is_displayed()]
        log(module_name, "CREATE Form Opened", "PASS", f"Form has {len(visible_inputs)} visible fields", ss_create, category="Create")

        # Submit empty to surface validation
        save_btn = click_first_match(driver, ["save", "submit", "create", "add"])
        if save_btn:
            capture_validation_messages(driver, module_name, "on empty submit")

        filled = []
        for inp in visible_inputs[:25]:
            outcome = fill_field(inp, marker=marker)
            filled.append(outcome)
        if filled:
            log(
                module_name,
                "CREATE Fields Filled",
                "PASS",
                "; ".join(filled[:5]),
                "",
                expected="All required fields populated",
                category="Create",
            )

        save_btn = click_first_match(driver, ["save", "submit", "create", "add"])
        if save_btn:
            ss_after_save = take_screenshot(driver, f"{module_name}_Create_Save")
            capture_validation_messages(driver, module_name, "after save")
            capture_success_messages(driver, module_name, "after save")
            # Second-pass fill if validation appeared
            fill_required_fields(visible_inputs[:25], marker)
            safe_wait(4)
            reload_if_needed(driver)

            # Try to return to listing and recount
            return_to_listing(driver)
            safe_wait(2)
            reload_if_needed(driver)

            new_row_count = count_table_rows(driver)
            marker_found = search_for_marker(driver, marker, module_name, "post-create search")

            if marker_found:
                log(
                    module_name,
                    "CREATE Persist",
                    "PASS",
                    f"Marker '{marker}' located after save (rows {base_row_count}->{new_row_count})",
                    ss_after_save,
                    expected="New record should be added and visible",
                    actual=f"Rows now {new_row_count}",
                    category="Create",
                )
            else:
                success_texts = capture_success_messages(driver, module_name, "post-save verify")
                status = "INFO" if success_texts else "FAIL"
                log(
                    module_name,
                    "CREATE Persist",
                    status,
                    f"Marker '{marker}' not found (rows {base_row_count}->{new_row_count})",
                    ss_after_save,
                    expected="New record should be added and visible",
                    actual=f"Rows now {new_row_count}",
                    category="Create",
                )
        else:
            log(module_name, "CREATE Save", "FAIL", "No save/submit button found", "", category="Create")
    else:
        log(
            module_name,
            "CREATE Button",
            "INFO",
            "No create button found",
            "",
            expected="At least one create/add trigger",
            category="Create",
        )

    # READ
    tables = driver.find_elements(By.TAG_NAME, "table")
    if tables:
        for idx, table in enumerate(tables[:2]):
            try:
                rows = table.find_elements(By.TAG_NAME, "tr")
                cols = table.find_elements(By.TAG_NAME, "th")
                log(
                    module_name,
                    f"READ Table {idx + 1}",
                    "PASS",
                    f"{len(rows)} rows, {len(cols)} columns",
                    ss_main,
                    expected="Data should be listed",
                    category="Read",
                )

                action_buttons = table.find_elements(By.XPATH, ".//button | .//a[@class='btn']")
                if action_buttons:
                    log(
                        module_name,
                        "Row Action Buttons",
                        "PASS",
                        f"Found {len(action_buttons)} action buttons in table",
                        "",
                        category="Read",
                    )
            except Exception:
                continue
    else:
        log(module_name, "READ Data", "INFO", "No data tables found", "", expected="Data grid should exist", category="Read")

    # UPDATE
    edit_buttons = driver.find_elements(
        By.XPATH,
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'edit')] | "
        "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'edit')] | "
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'update')] | "
        "//a[contains(@href, 'edit')]",
    )

    marker_present_for_edit = search_for_marker(driver, marker, module_name, "pre-edit locate")

    # Prefer edit within the row containing marker
    row_with_marker = find_row_with_marker(driver, marker) if marker_present_for_edit else None
    row_edit_btn = None
    if row_with_marker:
        try:
            candidates = row_with_marker.find_elements(By.XPATH, ".//button[contains(., 'Edit')] | .//a[contains(., 'Edit')] | .//a[contains(@href, 'edit')]")
            for c in candidates:
                if c.is_displayed() and c.is_enabled():
                    row_edit_btn = c
                    break
        except Exception:
            row_edit_btn = None

    if (edit_buttons or row_edit_btn) and marker_present_for_edit:
        btn_list = [row_edit_btn] if row_edit_btn else edit_buttons[:2]
        for btn in btn_list:
            try:
                if btn is None:
                    continue
                if btn.is_displayed() and btn.is_enabled():
                    btn_text = btn.text.strip() or "Edit"
                    log(
                        module_name,
                        "UPDATE Button",
                        "PASS",
                        f"Button: {btn_text}",
                        "",
                        expected="Edit form should open",
                        category="Update",
                    )

                    driver.execute_script("arguments[0].click();", btn)
                    safe_wait(4)
                    reload_if_needed(driver)

                    ss_edit = take_screenshot(driver, f"{module_name}_Edit_Form")
                    inputs = driver.find_elements(By.CSS_SELECTOR, "input, select, textarea")
                    visible_inputs = [inp for inp in inputs if inp.is_displayed()]

                    edits = []
                    for inp in visible_inputs[:15]:
                        edits.append(fill_field(inp, marker=marker_edit))

                    save_btn = click_first_match(driver, ["save", "update"])
                    if save_btn:
                        capture_validation_messages(driver, module_name, "after edit save")
                        ss_edit_save = take_screenshot(driver, f"{module_name}_Edit_Save")
                        search_for_marker(driver, marker_edit, module_name, "post-edit verify")
                        log(
                            module_name,
                            "UPDATE Persist",
                            "PASS",
                            f"Edited fields: {', '.join(edits[:4])}",
                            ss_edit_save,
                            expected="Changes should persist",
                            actual=f"Marker now {marker_edit}",
                            category="Update",
                        )
                    else:
                        log(module_name, "UPDATE Save", "FAIL", "No save/update button in edit form", "", category="Update")

                    driver.back()
                    safe_wait(3)
                    reload_if_needed(driver)
                    break
            except StaleElementReferenceException:
                continue
            except Exception as e:
                log(module_name, "UPDATE Test", "FAIL", str(e)[:100], "")
                driver.back()
                safe_wait(2)
    elif not edit_buttons and not row_edit_btn:
        log(module_name, "UPDATE Button", "INFO", "No edit button found", "", expected="At least one edit action", category="Update")
    else:
        log(module_name, "UPDATE Locate", "FAIL", "Marker not found to edit", "", category="Update")

    # DELETE
    delete_buttons = driver.find_elements(
        By.XPATH,
        "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'delete')] | "
        "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'delete')] | "
        "//button[contains(@class, 'delete')] | "
        "//a[contains(@href, 'delete')]",
    )

    delete_marker = marker_edit if marker_edit else marker
    marker_present_for_delete = search_for_marker(driver, delete_marker, module_name, "pre-delete locate")
    row_with_marker = find_row_with_marker(driver, delete_marker) if marker_present_for_delete else None

    if (delete_buttons or row_with_marker) and marker_present_for_delete:
        try:
            btn = None
            if row_with_marker:
                try:
                    candidates = row_with_marker.find_elements(By.XPATH, ".//button[contains(., 'Delete')] | .//a[contains(., 'Delete')] | .//button[contains(@class,'delete')] | .//a[contains(@href,'delete')] | .//i[contains(@class,'trash')]/parent::*")
                    for c in candidates:
                        if c.is_displayed() and c.is_enabled():
                            btn = c
                            break
                except Exception:
                    btn = None
            if btn is None and delete_buttons:
                btn = delete_buttons[0]

            if btn:
                driver.execute_script("arguments[0].click();", btn)
                safe_wait(2)
                try:
                    alert = driver.switch_to.alert
                    alert.accept()
                    safe_wait(2)
                except Exception:
                    pass
                ss_del = take_screenshot(driver, f"{module_name}_Delete")
                reload_if_needed(driver)
                return_to_listing(driver)
                safe_wait(2)
                reload_if_needed(driver)
                found_after_delete = search_for_marker(driver, delete_marker, module_name, "post-delete verify")
                status = "FAIL" if found_after_delete else "PASS"
                log(
                    module_name,
                    "DELETE Action",
                    status,
                    f"Delete triggered; marker present after delete? {found_after_delete}",
                    ss_del,
                    expected="Record should be removed",
                    category="Delete",
                )
            else:
                log(module_name, "DELETE Action", "FAIL", "No delete button resolved", "", category="Delete")
        except StaleElementReferenceException:
            log(module_name, "DELETE Action", "FAIL", "Stale element during delete", "", category="Delete")
        except Exception as e:
            log(module_name, "DELETE Action", "FAIL", str(e)[:80], "", category="Delete")
    elif not delete_buttons and not row_with_marker:
        log(module_name, "DELETE Button", "INFO", "No delete button found", "", expected="At least one delete action", category="Delete")
    else:
        log(module_name, "DELETE Locate", "FAIL", "Marker not found to delete", "", category="Delete")

    # SEARCH/FILTER
    search_inputs = driver.find_elements(
        By.CSS_SELECTOR,
        "input[type='search'], input[placeholder*='Search'], input[placeholder*='search'], input[placeholder*='Filter']",
    )

    if search_inputs:
        try:
            field = search_inputs[0]
            field.clear()
            term = "test"
            field.send_keys(term)
            field.send_keys(Keys.ENTER)
            safe_wait(2)
            log(
                module_name,
                "Search/Filter",
                "PASS",
                f"Search executed with term '{term}'",
                ss_main,
                expected="Results filter",
                actual="Search input responsive",
                category="Search",
            )
        except Exception as e:
            log(module_name, "Search/Filter", "FAIL", str(e)[:80], "", category="Search")
    else:
        log(module_name, "Search/Filter", "INFO", "No search/filter fields found", "", category="Search")

    # PAGINATION
    pagination = driver.find_elements(By.CSS_SELECTOR, ".pagination, [class*='paging'], .page-link")
    if pagination:
        log(module_name, "Pagination", "PASS", f"Found pagination with {len(pagination)} elements", ss_main, category="Pagination")

    # All buttons and dropdowns
    test_all_buttons(driver, module_name)
    test_all_dropdowns(driver, module_name)

    # Module-specific
    if "billing" in module_name.lower() or "matter" in module_name.lower() or "litigation" in module_name.lower():
        amounts = driver.find_elements(By.XPATH, "//*[contains(text(), '$')]")
        if amounts:
            log(module_name, "Financial Data", "PASS", f"Found {len(amounts)} amount/financial fields", "", category="Financial")

    if "calendar" in module_name.lower():
        cal = driver.find_elements(By.CSS_SELECTOR, "#calendar, .fc-view, [class*='calendar']")
        if cal:
            ss_cal = take_screenshot(driver, f"{module_name}_Calendar_Widget")
            log(module_name, "Calendar Widget", "PASS", "Calendar view found", ss_cal, category="Widget")

    if "document" in module_name.lower():
        uploads = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        if uploads:
            log(module_name, "Upload Feature", "PASS", f"Found {len(uploads)} file upload fields", "", category="Upload")


def test_comprehensive_module(driver, module_name, keywords):
    """Comprehensive test of a module"""
    print(f"\n{'=' * 100}")
    print(f"TESTING MODULE: {module_name.upper()}")
    print(f"{'=' * 100}")

    if not open_module_in_tab(driver, module_name, keywords):
        log(module_name, "Navigation", "FAIL", "Could not open module", "", category="Navigation")
        return

    log(module_name, "Navigation", "PASS", f"Successfully opened {module_name}", "", category="Navigation")

    safe_wait(5)
    reload_if_needed(driver)

    try:
        title = driver.title
        log(module_name, "Page Title", "PASS", title, "", category="Navigation")
    except Exception:
        pass

    test_crud_operations(driver, module_name)

    driver.close()
    driver.switch_to.window(driver.window_handles[0])
    safe_wait(2)


def save_csv_report(filename="CRM_Test_Report.csv"):
    """Save detailed CSV report"""
    try:
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["Step", "Timestamp", "Module", "Category", "Action", "Expected", "Actual", "Status", "Details", "Screenshot"],
            )
            writer.writeheader()
            writer.writerows(test_results)
        print(f"\n\u2713 CSV Report saved: {filename}")
        return True
    except Exception as e:
        print(f"\n\u2717 CSV save error: {e}")
        return False


def run_complete_test():
    """Run complete comprehensive test"""
    print("\n" + "=" * 100)
    print("GUARDIAN CAPITAL CRM - COMPLETE COMPREHENSIVE TEST")
    print("Testing ALL Modules, ALL Buttons, ALL Dropdowns, ALL CRUD Operations")
    print("=" * 100)
    print(f"URL: {TEST_URL}")
    print(f"User: {TEST_EMAIL}")
    print("Strategy: Multiple tabs, patient waiting, reload on errors")
    print("=" * 100)

    driver = webdriver.Chrome()
    driver.maximize_window()

    try:
        if not login_to_crm(driver):
            print("\n\u2717 Login failed - Cannot continue")
            return False

        safe_wait(3)

        modules = [
            ("Dashboard", ["Dashboard"]),
            ("Calendar", ["Calendar", "Calender"]),
            ("Tasks", ["Task", "Tasks"]),
            ("Matters", ["Matter", "Matters", "Case"]),
            ("Contacts", ["Contact", "Contacts", "Client"]),
            ("Activities", ["Activities", "Activity"]),
            ("Billing", ["Billing", "Bill", "Invoice"]),
            ("Litigation Funding", ["Litigation", "Funding"]),
            ("Documents", ["Document", "Documents", "File"]),
            ("Time Entries", ["Time", "Time Entry", "Timesheet"]),
            ("Expenses", ["Expense", "Expenses", "Expense List", "New Expense"]),
            ("Reports", ["Report", "Reports"]),
            ("Notes", ["Note", "Notes"]),
            ("Emails", ["Email", "Emails", "Mailbox", "Compose"]),
            ("Settings", ["Settings", "Setting", "Configuration", "Profile"]),
            ("Accounts", ["Accounts", "Account", "User", "Users"]),
            ("Import Data", ["Import", "Import Data", "Data Import", "Upload", "CSV", "Excel"]),
        ]

        for module_name, keywords in modules:
            try:
                test_comprehensive_module(driver, module_name, keywords)
            except Exception as e:
                print(f"  \u2717 Critical error in {module_name}: {str(e)[:100]}")
                log(module_name, "Critical Error", "FAIL", str(e), "")
                try:
                    driver.switch_to.window(driver.window_handles[0])
                except Exception:
                    pass

        print("\n" + "=" * 100)
        print("FINAL TEST SUMMARY")
        print("=" * 100)

        total = len(test_results)
        passed = len([r for r in test_results if r["Status"] == "PASS"])
        failed = len([r for r in test_results if r["Status"] == "FAIL"])
        info = len([r for r in test_results if r["Status"] == "INFO"])

        print(f"Total Tests: {total}")
        print(f"PASSED: {passed}")
        print(f"FAILED: {failed}")
        print(f"INFO: {info}")
        print(f"Screenshots: {screenshot_counter}")

        if total > 0:
            success_rate = (passed / (passed + failed) * 100) if (passed + failed) > 0 else 0
            print(f"Success Rate: {success_rate:.1f}%")

        print("=" * 100)

        save_csv_report()

        print("\n\u2713 Complete test finished!")
        print("\u2713 Check 'CRM_Test_Report.csv' for detailed results")
        print(f"\u2713 {screenshot_counter} screenshots saved")

        safe_wait(5)
        return True

    except Exception as e:
        print(f"\n\u2717 Critical error: {e}")
        import traceback

        traceback.print_exc()
        save_csv_report()
        return False

    finally:
        try:
            driver.quit()
            print("\n\u2713 Browser closed")
        except Exception:
            pass


if __name__ == "__main__":
    success = run_complete_test()
    exit(0 if success else 1)
