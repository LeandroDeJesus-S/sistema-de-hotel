from exc import Result
from payments.domain.entities import Payment


class AbsPDFGenerator:
    """Interface for a PDF generator."""

    def generate(self, data: Payment, locale: str = 'en') -> Result[bytes]:  # type: ignore
        """Generates a PDF from the given data.

        Args:
            data: The data to be used to generate the PDF.
            locale: The locale code for PDF content translation (e.g., 'en', 'pt-br').

        Returns:
            A Result containing the generated PDF on success, or an Error on failure.
        """
        ...
