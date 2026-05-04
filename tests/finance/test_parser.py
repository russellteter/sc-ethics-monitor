import pytest

from src.finance.parser import ParseError, ReportNumbers, parse_report_detail


def test_parses_heather_bauer_three_numbers(heather_bauer_html):
    """The captured Angular-rendered fixture parses to the three target numbers.

    Per PARSER_NOTES.md, the live page shows 89,372.11 (not 89,371.11 in the
    user-supplied prompt). We trust the live page.
    """
    nums = parse_report_detail(heather_bauer_html)
    assert nums == ReportNumbers(
        period_raised=32806.90,
        total_raised=89372.11,
        cash_on_hand=68448.57,
    )


def test_raises_on_empty_html():
    with pytest.raises(ParseError):
        parse_report_detail("<html><body>No data here</body></html>")


def test_raises_on_negative_numbers():
    """Negative amounts in receipts/COH rows are not legitimate — bail."""
    html = """
    <html><body>
      <table>
        <tr><td>Cash Contributions</td><td>$10.00</td><td>$10.00</td></tr>
        <tr><td>Total</td><td>$-100.00</td><td>$50.00</td></tr>
        <tr><td>Campaign Funds</td><td>$0.00</td><td>$25.00</td></tr>
      </table>
    </body></html>
    """
    with pytest.raises(ParseError):
        parse_report_detail(html)


def test_handles_dollar_sign_and_commas():
    """Currency formatting (``$1,234,567.89``) survives parsing."""
    html = """
    <html><body>
      <table>
        <tr><td>Cash Contributions</td><td>$1,234,567.89</td><td>$2,345,678.90</td></tr>
        <tr><td>Total</td><td>$1,234,567.89</td><td>$2,345,678.90</td></tr>
        <tr><td>Campaign Funds</td><td>$0.00</td><td>$3,456.78</td></tr>
      </table>
    </body></html>
    """
    nums = parse_report_detail(html)
    assert nums.period_raised == 1234567.89
    assert nums.total_raised == 2345678.90
    assert nums.cash_on_hand == 3456.78


def test_uses_first_total_after_cash_contributions():
    """Two ``Total`` rows exist (receipts + expenditures). Parser picks the receipts one."""
    html = """
    <html><body>
      <table>
        <tr><td>Cash Contributions</td><td>$100.00</td><td>$200.00</td></tr>
        <tr><td>Total</td><td>$100.00</td><td>$200.00</td></tr>
        <tr><td>Expenditures</td><td>$50.00</td><td>$50.00</td></tr>
        <tr><td>Total</td><td>$50.00</td><td>$50.00</td></tr>
        <tr><td>Campaign Funds</td><td>$25.00</td><td>$150.00</td></tr>
      </table>
    </body></html>
    """
    nums = parse_report_detail(html)
    # Receipts total wins, NOT expenditures total.
    assert nums.period_raised == 100.00
    assert nums.total_raised == 200.00
    assert nums.cash_on_hand == 150.00


def test_raises_when_total_row_missing():
    html = """
    <html><body>
      <table>
        <tr><td>Cash Contributions</td><td>$100.00</td><td>$200.00</td></tr>
        <tr><td>Campaign Funds</td><td>$25.00</td><td>$150.00</td></tr>
      </table>
    </body></html>
    """
    with pytest.raises(ParseError):
        parse_report_detail(html)


def test_raises_when_campaign_funds_missing():
    html = """
    <html><body>
      <table>
        <tr><td>Cash Contributions</td><td>$100.00</td><td>$200.00</td></tr>
        <tr><td>Total</td><td>$100.00</td><td>$200.00</td></tr>
      </table>
    </body></html>
    """
    with pytest.raises(ParseError):
        parse_report_detail(html)


def test_handles_two_column_total_fallback():
    """Some templates may render only Label | Aggregate (2 columns).

    In that case, period_raised is unknowable; parser must raise rather than guess.
    """
    html = """
    <html><body>
      <table>
        <tr><td>Cash Contributions</td><td>$200.00</td></tr>
        <tr><td>Total</td><td>$200.00</td></tr>
        <tr><td>Campaign Funds</td><td>$150.00</td></tr>
      </table>
    </body></html>
    """
    with pytest.raises(ParseError):
        parse_report_detail(html)
