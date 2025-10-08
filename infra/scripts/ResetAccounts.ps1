# Check if Microsoft.Graph module is installed
if (-not (Get-Module -ListAvailable -Name Microsoft.Graph)) {
    Write-Host "Microsoft.Graph module not found. Installing..." -ForegroundColor Yellow
    Install-Module -Name Microsoft.Graph -Force -Scope CurrentUser
}

# Import the Microsoft Graph module
Import-Module Microsoft.Graph.Users -Force

# Log in to Microsoft Graph
Write-Host "Logging in to Microsoft Graph..." -ForegroundColor Cyan
Connect-MgGraph -Scopes "User.ReadWrite.All"

# Define the array of user accounts
# Replace these with the actual user accounts (UPNs)
$userAccounts = @(
    "username1@example.com",
    "username2@example.com",
    "username3@example.com",
    "username4@example.com",
    "username5@example.com",
    "username6@example.com",
    "username7@example.com",
    "username8@example.com",
    "username9@example.com",
    "username10@example.com",
    "username11@example.com",
    "username12@example.com"
)

# Define the output CSV file path
$outputCsvPath = "./ResetAccountsOutput.csv"

# Initialize an array to store the results
$results = @()

# Loop through each user account
foreach ($user in $userAccounts) {
    try {
        # Generate a new random password (12 characters with at least 2 special characters)
        $chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*"
        $newPassword = -join ((1..12) | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
        
        # Ensure at least one uppercase, one lowercase, one digit, and one special character
        $newPassword = "A" + "a" + "1" + "!" + (-join ((1..8) | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] }))

        # Reset the user's password using Microsoft Graph
        $passwordProfile = @{
            Password = $newPassword
            ForceChangePasswordNextSignIn = $false
        }
        
        Update-MgUser -UserId $user -PasswordProfile $passwordProfile

        # Add the result to the array
        $results += [PSCustomObject]@{
            UserPrincipalName = $user
            NewPassword       = $newPassword
        }

        Write-Host "Password reset for $user successfully." -ForegroundColor Green
    } catch {
        Write-Host "Failed to reset password for $user`: $_" -ForegroundColor Red
    }
}

# Export the results to a CSV file
$results | Export-Csv -Path $outputCsvPath -NoTypeInformation

Write-Host "Password reset process completed. Results saved to $outputCsvPath" -ForegroundColor Cyan