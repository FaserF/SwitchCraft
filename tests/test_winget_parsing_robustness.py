import pytest
from switchcraft_winget.utils.winget import WingetHelper

# Sample outputs based on real Winget CLI behavior
# English Output
SAMPLE_OUTPUT_EN = """
Name                               Id                               Version          Source
---------------------------------------------------------------------------------------
Mozilla Firefox                    Mozilla.Firefox                  121.0            winget
Google Chrome                      Google.Chrome                    120.0.6099.130   winget
Visual Studio Code                 Microsoft.VisualStudio.Code      1.85.1           winget
"""

# German Output (Note: "Quelle" instead of "Source")
SAMPLE_OUTPUT_DE = """
Name                               Id                               Version          Quelle
---------------------------------------------------------------------------------------
Mozilla Firefox                    Mozilla.Firefox                  121.0            winget
Google Chrome                      Google.Chrome                    120.0.6099.130   winget
Visual Studio Code                 Microsoft.VisualStudio.Code      1.85.1           winget
"""

# Tricky Output (Spaces in names, weird versions)
SAMPLE_OUTPUT_TRICKY = """
Name                               Id                               Version          Source
---------------------------------------------------------------------------------------
PowerToys (Preview)                Microsoft.PowerToys              0.76.0           winget
AnyDesk                            AnyDeskSoftwareGmbH.AnyDesk      7.1.13           winget
Node.js                            OpenJS.NodeJS                    20.10.0          winget
"""

# Output with no header found (Edge case)
SAMPLE_OUTPUT_NO_HEADER = """
No packages found.
"""

def test_parse_search_results_en():
    helper = WingetHelper()
    results = helper._parse_search_results(SAMPLE_OUTPUT_EN)
    assert len(results) == 3
    assert results[0]['Name'] == "Mozilla Firefox"
    assert results[0]['Id'] == "Mozilla.Firefox"
    assert results[0]['Version'] == "121.0"
    assert results[0]['Source'] == "winget"

def test_parse_search_results_de():
    helper = WingetHelper()
    results = helper._parse_search_results(SAMPLE_OUTPUT_DE)
    assert len(results) == 3
    assert results[0]['Name'] == "Mozilla Firefox"
    assert results[0]['Id'] == "Mozilla.Firefox"
    assert results[0]['Source'] == "winget"

def test_parse_search_results_tricky():
    helper = WingetHelper()
    results = helper._parse_search_results(SAMPLE_OUTPUT_TRICKY)
    assert len(results) == 3
    assert results[0]['Name'] == "PowerToys (Preview)"
    assert results[0]['Id'] == "Microsoft.PowerToys"

def test_parse_search_results_empty():
    helper = WingetHelper()
    results = helper._parse_search_results(SAMPLE_OUTPUT_NO_HEADER)
    assert len(results) == 0
