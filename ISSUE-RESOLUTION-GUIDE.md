Here is a detailed document covering various issues encountered, their root causes, and resolution steps, drawing on all the provided sources.

---

# Comprehensive Troubleshooting Guide: Quantbase Support Issues

This document provides detailed information on common issues encountered by Quantbase users, including their underlying causes and step-by-step instructions for resolution and debugging.

## 1. Bank Account & Deposit-Related Issues

### 1.1 Users Stuck in Onboarding or Unable to Update Bank Account Due to Failed Deposits and Alpaca Restrictions

This is a frequently reported issue where users face hurdles in the onboarding process or cannot modify their bank account details.

*   **Reason for Issue (Root Cause):**
    *   Users often initially connect an **incorrect bank account** via Plaid, leading to **failed initial ACH transfers**.
    *   These failed transfers trigger **Alpaca account restrictions**, commonly setting the account to "restricted to liquidation" due to ACH return flags. This restricted state causes Alpaca APIs to return limited or incorrect data to the Quantbase dashboard.
    *   **Outdated bank credentials and Plaid-related fields** (`relationship_id`, `plaid_access_token`, `plaid_account_id`, `initial_funding_amount`, `bank_account_nickname`) remain in the system, preventing users from re-linking a new bank account or continuing onboarding.
    *   Failed deposits incur a **$25 fee**. Alpaca might require this fee to be paid before lifting restrictions, though they may still decline to support the account even after payment.
    *   In some cases, a **client-side UI bug** can prevent manual bank account reconnection attempts, causing a submit button to spin indefinitely.

*   **Steps to Resolve or Debug the Issue:**

    1.  **Identify and Verify the Issue:**
        *   The user will typically report being stuck in onboarding or unable to update bank details.
        *   **Log in as the customer** via the support portal.
        *   Check the **transfers page for failed transfers** (status "returned").
        *   Confirm if **deposits are disabled**.
        *   Verify Alpaca restriction by querying the **Alpaca trading API** (`GET https://broker-api.alpaca.markets/v1/trading/accounts/{account_id}/account`) and checking for `"restrict_to_liquidation_reasons": {"ach_return": true}` in the response.
        *   If the dashboard shows an incorrect balance (e.g., $0 or demo data), it could be due to Alpaca restrictions.

    2.  **Cancel Active AutoInvestments (if applicable):**
        *   If the issue involves an unauthorized transaction before account closure, likely due to an active AutoInvest setup:
            *   Navigate to the user's dashboard and **manually delete each active AutoInvest setup**.

    3.  **Address Failed Deposit Fees and Alpaca Account Locks/Restrictions:**
        *   Inform the user that failed deposits typically incur a **$25 fee**.
        *   **Contact Alpaca for unlocking/restriction removal**:
            *   If the account is **locked due to a returned transfer**, email Alpaca using the template: "Hey, Alpaca, I have a user with a turn transfer whose account is locked. Could you please assist unlock the account?" Include "cashier's team" in the subject and the user's **Alpaca code**. Alpaca support operates Monday through Friday.
            *   If the account is in a **restricted state**, advise Customer Support to **send a support request to Alpaca to remove the restriction**. Alpaca might require the $25 fee, but may still decline to support the account.

    4.  **Reset User's Bank Account and Onboarding Status in the Database:**
        *   This is crucial for users stuck due to outdated bank credentials.
        *   **Connect to the production database**.
        *   In the `mainpage_users` table: find the user record and **set the following fields to `NULL`**: `relationship_id`, `plaid_access_token`, `plaid_account_id`, `initial_funding_amount`, `bank_account_nickname`.
        *   In the `mainpage_onboardingstatus` table: find the user's onboarding status record and **reset the state to `alpaca_app_submitted`**.
        *   **Save these changes**. This allows users to re-link a new bank account and restart onboarding.

    5.  **Manual Bank Account Entry (Last Resort):**
        *   If the user is still unable to connect via the UI, or if Alpaca has declined reinstatement, you may need to **manually enter bank account details** into Alpaca on their behalf.
        *   Request the user to email the following details: `routing_no`, `account_no`, `account_type` (i.e., Saving or Checking), `nick_name`.

    6.  **Communicate with the User:**
        *   Inform the user they can now **re-link their bank account** and restart onboarding.
        *   If an Alpaca restriction was lifted, explain that account values should now display properly.
        *   If a negative balance was reported, explain it's often a timing artifact that will normalize.

*   **Important Notes:**
    *   **Money Laundering Prevention (AML):** If a user attempts to withdraw their entire balance to a *new* bank account after a failed transfer, Alpaca requires verification of ownership for *both* the old and new accounts by uploading account statements.
    *   Even after database updates, an **email to Alpaca is typically required to get the new bank account officially approved**.

### 1.2 Deposits Disabled Due to Failed Deposit

Users find they can no longer make deposits.

*   **Reason for Issue (Root Cause):**
    *   Deposits are almost exclusively disabled because of a **failed deposit**. This can occur due to an "invalid account number structure" or other issues leading to an ACH return.
    *   Failed deposits incur a **$25 fee**.

*   **Steps to Resolve or Debug the Issue:**
    1.  **Verify Failed Transfer:** Log in as the user and go to the transfers page to see if a deposit is marked as "returned".
    2.  **Communicate with User:** Ask the user to contact their bank or update their connected bank account details. Inform them about the $25 fee, which is charged to prevent future failures and fees.
    3.  **Alpaca Account Unlock:** If not already done, an email to Alpaca may be required to unlock their account, following the procedure in section 1.1.

### 1.3 Bank Account Change Failed (Wrong Code Submitted)

A user attempts to change their bank account but the process completes unusually quickly, or fails.

*   **Reason for Issue (Root Cause):**
    *   The user submitted a `bank relationship ID` (code) that **does not match the one provided by the system**. This often happens if they used an old code, or deleted and recreated their account details, generating a new code.

*   **Steps to Resolve or Debug the Issue:**
    1.  **Check Docker Logs:** If the bank account change submission completes very quickly (not the usual ~30 seconds), check Docker logs for "bank relationship ID does not match".
    2.  **Verify Code in Database:** Look up the user in the `mainpage_users` table in the database to compare the submitted code with the system's `bank relationship code`.
    3.  **Inform User:** Let the user know the submitted code is no longer valid and they should **recreate their account details to generate a new code and send that**.

### 1.4 Bank Account Change (Successful Process)

When a user successfully changes their bank account.

*   **Steps for Processing:**
    1.  **Initiate Change:** Log in as the user, paste the new bank account code, and hit submit.
    2.  **Monitor Progress:** A successful submission typically takes **10 to 30 seconds**. You can follow along by checking Docker logs, which will show requests to Alpaca to delete the old bank account relationship (with long polling) and then submit the new one.
    3.  **Confirm and Notify:** Once the logs indicate completion, respond to the user using the "account updated" template.

### 1.5 Knowing Which Linked Account an Outgoing Transfer is Going Towards

A user wants to identify the destination bank for their withdrawal.

*   **Steps to Resolve:**
    1.  **Log in as User:** Access the user's account via the support portal.
    2.  **Find Routing Number:** Navigate to the page showing account details and locate the **routing number**.
    3.  **Use ABA Lookup:** Go to the American Banker's Association (ABA) website, search using the routing number to identify the bank (e.g., Bank of America).
    4.  **Direct Communication:** Inform the user directly of the bank's name.

## 2. Account Status & Balance Display Issues

### 2.1 Dashboard Shows Incorrect Balance for Restricted Alpaca Accounts

Users report that their dashboard displays $0 or incorrect/missing account balances and portfolio values.

*   **Reason for Issue (Root Cause):**
    *   The user's Alpaca account is in a **"restricted to liquidation" state** due to ACH return flags.
    *   This restriction causes Alpaca APIs to return **limited or inaccurate data**, leading to incorrect values on the Quantbase dashboard.

*   **Steps to Resolve or Debug the Issue:**
    1.  **Collect Alpaca Account ID:** Obtain the user's Alpaca account ID.
    2.  **Confirm Restriction:** Query the Alpaca trading API (`GET https://broker-api.alpaca.markets/v1/trading/accounts/{account_id}/account`) and verify the presence of `"restrict_to_liquidation_reasons": {"ach_return": true}` in the response.
    3.  **Request Restriction Removal:** Advise Customer Support to send a support request to Alpaca to remove the restriction.
    4.  **Inform User:** Let the user know their account is restricted by Alpaca, and that values will display properly once the restriction is lifted.

### 2.2 Negative Balance Displayed Despite Account Unrestriction

A user reports a negative available balance on their dashboard even after Alpaca restrictions have been lifted.

*   **Reason for Issue (Root Cause):**
    *   This is **not a bug but a "timing artifact"**. The dashboard's available balance calculation (`available = available_balance - tied_up_cash['total']`) deducts all pending or non-available amounts.
    *   "Tied-up cash" can include pending ACH transfer deposits, pending transactions in strategies, open cash positions, unpaid fee charges, and pending journals.
    *   Even if Alpaca shows a positive buying power, these deductions can result in a temporarily negative display on the Quantbase dashboard until funds settle or transactions complete.

*   **Steps to Resolve or Debug the Issue:**
    1.  **Verify Unrestriction:** Confirm that the Alpaca account was successfully unrestricted via API.
    2.  **Identify Tied-Up Cash:** Investigate the source of the negative balance by understanding the `_calculate_tied_up_cash` method's logic, which deducts various pending amounts.
    3.  **Explain to User:** Explain the computation steps and the nature of "tied-up cash" to the user. Inform them that the balance will **normalize once pending transfers and transactions are completed**.

### 2.3 User Stuck on Onboarding Page (Onboarding Complete)

A user reports being stuck on the onboarding page, but their account status indicates "onboarding complete."

*   **Reason for Issue (Root Cause):**
    *   Even if the backend `onboarding status` is `onboarding complete`, a user might still see the onboarding page.

*   **Steps to Resolve or Debug the Issue:**
    1.  **Verify Onboarding Status:** Grab the user's email, log into the support portal as them, and check their `Onboarding Status`. If it says **`onboarding complete`**, they have access to their dashboard.
    2.  **Instruct to Wait:** Advise the user to **"just wait one hour, one day, two days"**. Access should resolve on its own.

### 2.4 User Believes Account Setup is Complete, but Cash Not Invested

A user thinks their account is fully set up, possibly after receiving a "cash has arrived" email, but their dashboard indicates otherwise or shows demo data.

*   **Reason for Issue (Root Cause):**
    *   The "Cash has arrived in your Coinbase account" step does not mean the entire setup is complete. The final step, "Your cash is invested," occurs at **market close** on that day.
    *   Before investment, the user might only have access to a demo dashboard.

*   **Steps to Resolve or Debug the Issue:**
    1.  **Review Onboarding Steps:** Remind the user of the full onboarding process: Personalize your portfolio, Submit your application (KYC), Cash transfer initiated, Cash arrives in your Coinbase account, **Your cash is invested**.
    2.  **Instruct to Wait:** Explain that the "Your cash is invested" step completes at market close, and they should **wait until aftermarket close** to gain full access to their account.

## 3. Account Closure & AutoInvest Issues

### 3.1 Account Closure (General Procedure)

A user requests to close their account.

*   **Prerequisites for Closure:**
    *   Local project instance connected to the **production database**.
    *   Admin credentials (e.g., user: Justin).
    *   **No pending transfers**.
    *   **Zero balances**: Buying power = $0, Account/equity value = $0, Settled balance = $0.
    *   The user has completed their part: sold everything, emptied their account, and their latest transfer was a withdrawal.

*   **Steps to Close an Account:**
    1.  **Log in as Admin** and then **Login as Customer** via the `/dev/support` portal.
    2.  **Verify Account Eligibility** by checking for pending transfers and ensuring all balances are $0 on the customer's dashboard.
    3.  **Grab User ID**.
    4.  **Database Update:** Connect to the database and update the user record in the `mainpage_users` table:
        *   Set `transfer_capabilities = 'X'` (no capabilities: no auto deposit, no auto investments, no deposits, no withdrawals).
        *   Set `deactivated = true`.
    5.  **Save changes**. This prevents the user from logging in or initiating transfers.
    6.  **Document Closure:** Comment on the Jira ticket that the account was closed successfully.

*   **Important Notes:**
    *   Double-check pending transfers and balances to avoid errors.
    *   Retain a screenshot of the customer’s $0 balance for audit purposes.
    *   While an API call to Alpaca can close the account on their side, it is noted as tech debt.

### 3.2 User Wants to Close Account (Funds Not Empty or Wrong Email)

A user requests account closure, but there are issues like remaining funds or an email address mismatch.

*   **Reason for Issue (Root Cause):**
    *   The user has closed their positions but **has not yet initiated a withdrawal**.
    *   The request to close the account comes from an **email address that is not tied to the Quantbase account**.

*   **Steps to Resolve or Debug the Issue:**
    1.  **Verify Email Address:** If the request comes from an untied email address, **do not take action**. Inform the user that you can only act on their behalf if the request originates from the email address tied to their account.
    2.  **Verify Fund Withdrawal:** If funds have not been withdrawn:
        *   Inform the user of the necessary steps: they first need to **close all positions**, then **initiate a withdrawal**.
        *   Explain they must **wait a few days** for the withdrawal to complete.
        *   Only after these steps are complete can the account closure process be finalized.

### 3.3 AutoInvest Triggered Unauthorized Transaction Before Account Closure

A user's AutoInvest schedule executed an automated transaction *after* they requested account closure but *before* the closure was complete.

*   **Reason for Issue (Root Cause):**
    *   The user's **AutoInvest schedules were still active** when the account closure request was made.
    *   These automated investments are scheduled independently of manual account activity, leading to a transaction being executed while the closure process was pending.

*   **Steps to Resolve or Debug the Issue:**
    1.  **Investigate and Cancel AutoInvestments:**
        *   Access the support dashboard and confirm active AutoInvestments.
        *   Navigate to the user's dashboard and **manually delete each active AutoInvest setup**.
    2.  **Divest and Withdraw:**
        *   Navigate to the user's dashboard, select each fund, and click "Sell" to **divest all invested funds**.
        *   **Wait 1-2 days for divestments to settle** and funds to become available as cash.
        *   **Manually transfer the available cash balance** back to the user's bank account.
    3.  **Perform Account Closure:**
        *   Connect to the production database and update the user record in `mainpage_users`:
            *   Set `transfer_capabilities = 'X'`
            *   Set `deactivated = true`.
        *   **Save changes**.
    4.  **Confirm Closure:** Notify via Jira ticket that the account was closed successfully.

### 3.4 User Trying to Withdraw Entire Balance to New Account (AML Concern)

A user attempts to withdraw their entire balance to a new bank account, especially after a failed transfer.

*   **Reason for Issue (Root Cause):**
    *   Withdrawing deposited money from one account to a *different* account signals potential **money laundering (AML)**. Money laundering involves obfuscating the origin and destination of funds.
    *   **Alpaca prevents this** without verifying ownership of both bank accounts.

*   **Steps to Resolve or Debug the Issue:**
    1.  **Unlock Alpaca Account:** First, email Alpaca to get the user's account unlocked, especially if there was a returned transfer. Use the specified template and include "cashier's team" in the subject line.
    2.  **Inform User about AML:** Communicate to the user that this action appears as an AML concern.
    3.  **Request Verification Documents:** Inform the user they must upload **account statements for *both* the old and new bank accounts** to verify ownership. These documents should contain the bank's name and logo, and the user's full name and address.
    4.  **Update Bank Account Information:** The user (or support) must first update their bank account information in the system by entering the new code and submitting it.
    5.  **Email Alpaca for Approval:** After documents are uploaded and the system is updated, an email must be sent to Alpaca to get the new account officially approved.

## 4. Other Specific Issues

### 4.1 Alpaca Account Reactivation Email Process

Customer support needs guidance on how to reactivate a user's Alpaca account.

*   **Reason for Issue (Root Cause):**
    *   Support team members may be unaware of the correct communication channel and necessary information for Alpaca account reactivation.

*   **Steps to Resolve or Debug the Issue:**
    1.  **Identify Official Email:** Determine the official Alpaca support email address.
    2.  **Email Request:** Inform support that reactivation requests **must be sent via email**.
    3.  **Include Alpaca User ID:** Clarify that the **Alpaca user ID must be included in the email** for proper routing and action.

### 4.2 Quivercoin Subscription Expired / Need to Update Code

A user receives an email about an expired Quivercoin subscription or needs to update their code after a subscription change.

*   **Reason for Issue (Root Cause):**
    *   If a user upgrades their subscription (e.g., to annual), ends a trial, or changes their plan, they typically **generate a new code** that needs to be updated on Quantbase.
    *   The system for checking Quivercoin subscriptions can sometimes incorrectly email people about expiration.

*   **Steps to Resolve or Debug the Issue:**
    1.  **Verify Subscription Status:** Log in as the user, navigate to the "care page," then "partnerships," and look at "group one" to see the actual subscription end date.
    2.  **Instruct User to Update Code:** If the subscription has ended or changed, explain that they generated a new code when they changed their subscription.
    3.  **Provide Instructions:** Guide them to find their new Quiverquant code and enter it on Quantbase. Provide deep links to the relevant pages to streamline the process.

### 4.3 Unpaid Fees and Transactions Management

Various issues related to unpaid fees, insufficient funds, or pending transactions.

*   **Reason for Issue (Root Cause):**
    *   **Missing Fees:** Fees like $10, 24 cents, $4, or $5 might be unaccounted for.
    *   **Insufficient Funds:** A user's account may not have enough money to cover a fee.
    *   **Negative Journal Balance:** Accounts can enter a state of negative journal balance.
    *   **Pending Journal Fund Settle:** Transactions may be pending until funds settle.
    *   **Imperfect Execution:** Selling very small amounts (e.g., 30 cents) can be imperfect in execution flow.
    *   **Pattern Day Trading Restrictions:** Some sell orders (e.g., liquidations to cover fees) might be subject to pattern day trading restrictions and execute on the next day.

*   **Steps to Resolve or Debug the Issue:**
    1.  **For Missing/Unpaid Fees:** If a fee is simply missing, "clear a transaction and start it again".
    2.  **For Insufficient Funds:** If there are insufficient funds in the account to pay a fee, **delete the associated transaction**.
    3.  **For Negative Journal Balance:** Run a process to fix the negative journal balance by adjusting account figures.
    4.  **For Pending Journal Fund Settle:** If a transaction is pending fund settlement, advise waiting a **couple of days** for the funds to clear.
    5.  **Initiate Execution Strategy:** Trigger an execution strategy to sell assets to cover fees. Note that some transactions might not fill immediately due to restrictions and will execute on the next business day. Once executed, funds need to settle before they are available for withdrawal.

### 4.4 Request to Open a Business Account

A user inquires about opening a business account with Quantbase.

*   **Reason for Issue (Root Cause):**
    *   Quantbase, through its integration with Alpaca, **does not support business accounts**.
    *   This is because business accounts require a complex Know Your Business (KYB) verification process, similar to KYC but for businesses, to verify their existence and track finances for money laundering/fraud prevention. Alpaca previously supported KYB but found it too difficult.

*   **Steps to Resolve:**
    1.  **Inform User:** Simply and directly tell the user that **Quantbase does not support business accounts**.

## General Support Best Practices

*   **Direct Communication:** When responding to users, be very **direct, provide clear answers, and avoid asking too many questions** in a single email. Simply respond to what they are looking for.
*   **Email Verification:** Always ensure that you only take action on behalf of a user if the request comes from the **exact email address tied to their account**.
*   **Documentation:** Comment on Jira tickets with resolution details and timestamps, and retain screenshots for audit purposes where appropriate.

---