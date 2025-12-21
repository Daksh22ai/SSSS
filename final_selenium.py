import time
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Import the necessary components from bip_utils
from bip_utils import (
    Bip39SeedGenerator, Bip39MnemonicValidator,
    Bip84, Bip84Coins, Bip44Changes
)

# --- CONFIGURATION ---
# Part 1: Selenium and Restoration Configuration
shares_to_restore = [
    "rocket ankle party unusual exercise humble surround expect train helmet away marriage",
    "mass sock lemon degree enact awful glad valve toilet shadow upset tunnel",
    "crime afford bronze merit light board fever box sign expire raccoon blade"
]

html_file_path = r"C:\Users\tulsi\Downloads\Bitcoin mnemonic code tools.html"

# This must be the full path to your msedgedriver.exe
driver_executable_path = r"C:\Daksh\SSSS\msedgedriver.exe" 
# The address you want to compare the recovered address against.
# Set this to your address string (bech32) to enable comparison.
target_address = "bc1qyjwa0tf0en4x09magpuwmt2smpsrlaxwn85lh6"


# --- SCRIPT LOGIC ---
service = EdgeService(executable_path=driver_executable_path)
driver = webdriver.Edge(service=service)
wait = WebDriverWait(driver, 10)

print("Browser opened successfully.")
restored_mnemonic = "" # Initialize variable to hold the secret

try:
    # ====== STAGE 1: RESTORE SECRET MNEMONIC USING SELENIUM ======
    
    driver.get("file:///" + html_file_path)
    print(f"Successfully loaded file: {html_file_path}")

    for i, share in enumerate(shares_to_restore):
        share_number = i + 1
        print(f"Processing share {share_number}...")

        if share_number > 2:
            print("  -> Clicking '+add share' button...")
            add_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[@onclick="add_share();"]')))
            driver.execute_script("arguments[0].scrollIntoView(true);", add_button)
            add_button.click()
            print("  -> Button clicked successfully.")

        input_box_id = f"share-input-{share_number}"
        share_input_box = wait.until(EC.visibility_of_element_located((By.ID, input_box_id)))
        share_input_box.send_keys(share)
        print(f"  -> Entered share into box #{share_number}.")

    print("\nAll shares entered. Looking for the 'Restore' button...")
    restore_button = wait.until(EC.presence_of_element_located((By.ID, "restore-btn")))
    driver.execute_script("arguments[0].click();", restore_button)
    print("Restore button clicked via JavaScript.")

    print("Waiting for restoration result...")
    restored_mnemonic_element = wait.until(EC.visibility_of_element_located((By.ID, "restored-result")))
    
    wait.until(lambda d: restored_mnemonic_element.get_attribute("value") != "")
    restored_mnemonic = restored_mnemonic_element.get_attribute("value")

finally:
    print("\nClosing the browser.")
    driver.quit()

# ====== STAGE 2: DERIVE ADDRESS FROM RESTORED MNEMONIC ======

print("\n" + "="*40)
if restored_mnemonic:
    print(f"✅ Secret restored successfully!")
    print(f"Restored Mnemonic: {restored_mnemonic}")
    
    try:
        # Validate the restored mnemonic
        if not Bip39MnemonicValidator().IsValid(restored_mnemonic):
            raise ValueError("Restored mnemonic phrase is not valid.")

        # Generate seed from the restored mnemonic
        print("\nGenerating seed from mnemonic...")
        seed_bytes = Bip39SeedGenerator(restored_mnemonic).Generate()

        # Create BIP84 wallet for Bitcoin mainnet
        print("Deriving BIP84 wallet...")
        bip84_wallet = Bip84.FromSeed(seed_bytes, Bip84Coins.BITCOIN)

        # Derive the specific address (m/84'/0'/0'/0/0)
        print("Deriving address at m/84'/0'/0'/0/0...")
        address = bip84_wallet.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0).PublicKey().ToAddress()
        
        print("\n" + "-"*40)
        print("🎉 Final Result 🎉")
        print(f"Bech32 Address: {address}")
        print("-" * 40)

        # --- ADDRESS COMPARISON ---
        # If a target address is configured, compare it with the derived address.
        if 'target_address' in globals() and target_address:
            try:
                if address.strip().lower() == target_address.strip().lower():
                    print("\n✅ Address match: the derived address matches the target address.")
                else:
                    print(f"\n❌ Address does not match. Expected: {target_address}")
            except Exception as cmp_e:
                print(f"\n⚠️ Error while comparing addresses: {cmp_e}")
        else:
            print("\n(No target address configured; skipping comparison.)")

    except Exception as e:
        print(f"\n❌ An error occurred during address derivation: {e}")

else:
    print("❌ Failed to restore the secret from shares. Cannot derive address.")

print("="*40)