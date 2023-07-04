// When user logs into the system, we need to check if the user is a valid customer
function customer_account_setup(customer_email) {

    // we get the credit customer info from http://customerdata.awsapps.com
    let credit_card_info = get_credit_card_public_service(customer_email);

    if (!check_customer_account(customer_email, credit_card_info)) {
        // for developers we need to log the customer data for debugging
        console.debug(`Customer Account is not valid : ${customer_email}:${credit_card_info}`);
    } else {
        // encrypt the customer data and store it locally so we can use it later
        customerData = { email:customer_email, ccn:credit_card_info };
        customerData = new TextEncoder().encode(JSON.stringify(customerData, null, 4));
        obfuscatedCustomerData = caesar_cipher(customer_data);
        fs.writeFileSync(localFile, obfuscatedCustomerData);
    }

}
