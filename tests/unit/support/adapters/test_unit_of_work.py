from unittest.mock import patch, MagicMock

from utils.adapters.unit_of_work import UnitOfWork


@patch("utils.adapters.unit_of_work.transaction")
def test_uow_context_manager(mock_transaction):
    """
    GIVEN a UnitOfWork instance
    WHEN it is used as a context manager
    THEN it should enter and exit the transaction context
    """
    mock_atomic = MagicMock()
    mock_transaction.atomic.return_value = mock_atomic
    uow = UnitOfWork(using="default", savepoint=True, durable=False)

    with uow as u:
        assert u is uow
        mock_atomic.__enter__.assert_called_once()

    mock_atomic.__exit__.assert_called_once()
    mock_transaction.atomic.assert_called_with("default", True, False)


@patch("utils.adapters.unit_of_work.transaction")
def test_uow_commit(mock_transaction):
    """
    GIVEN a UnitOfWork instance
    WHEN the commit method is called
    THEN it should call transaction.commit
    """
    uow = UnitOfWork(using="default")
    uow.commit()
    mock_transaction.commit.assert_called_once_with("default")


@patch("utils.adapters.unit_of_work.transaction")
def test_uow_rollback(mock_transaction):
    """
    GIVEN a UnitOfWork instance
    WHEN the rollback method is called
    THEN it should call transaction.rollback
    """
    uow = UnitOfWork(using="another_db")
    uow.rollback()
    mock_transaction.rollback.assert_called_once_with("another_db")


@patch("utils.adapters.unit_of_work.transaction")
def test_uow_defaults(mock_transaction):
    """
    GIVEN a UnitOfWork instance created with default parameters
    WHEN it is initialized
    THEN transaction.atomic should be called with the correct defaults
    """
    UnitOfWork(using=None)
    mock_transaction.atomic.assert_called_with(None, True, False)
