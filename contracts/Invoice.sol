pragma solidity ^0.4.20;

import "../node_modules/openzeppelin-solidity/contracts/math/SafeMath.sol";

contract Invoice {
    using SafeMath for uint256;

    enum Status { Active, Overdue, Paid }

    event Refund(
        address receiver,
        uint256 amount
    );

    event Payment(
        address from,
        uint256 amount
    );

    event Withdraw(
        address receiver,
        uint256 amount
    );

    uint256 public InvoiceAmount;
    uint256 public CurrentAmount;
    uint256 public ValidityPeriod;
    address public Beneficiary;
    address public Payer;
    address public PartialReceiver;
    string public Memo;
    address public Owner;

    bool internal WasPaid;

    constructor (
        uint256 _invoiceAmount,
        string _memo,
        address _beneficiary,
        address _payer,
        uint256 _validityPeriod,
        address _partialReceiver
    ) public {
        if (_validityPeriod != 0) {
            require(_validityPeriod > now);
            require(_partialReceiver == _payer || _partialReceiver == _beneficiary);
        }

        InvoiceAmount = _invoiceAmount;
        Memo = _memo;
        Beneficiary = _beneficiary;
        Payer = _payer;
        ValidityPeriod = _validityPeriod;
        PartialReceiver = _partialReceiver;
        CurrentAmount = 0;
        WasPaid = false;
        Owner = msg.sender;
    }

    modifier onlyPayer() {
        require(Payer == address(0) || msg.sender == Payer);
        _;
    }

    function getStatus() public view returns (Status) {
        if (WasPaid == true)
            return Status.Paid;
        if (ValidityPeriod != 0 && now > ValidityPeriod)
            return Status.Overdue;
        return Status.Active;
    }

    function doRefund(uint256 amount) internal {
        msg.sender.transfer(amount);
        emit Refund(msg.sender, amount);
    }

    function doWithdraw(address receiver, uint256 amount) internal {
        receiver.transfer(amount);
        emit Withdraw(receiver, amount);
    }

    function pay() public payable onlyPayer {
        if (getStatus() != Status.Active) {
            doRefund(msg.value);
            return;
        }

        uint256 will = CurrentAmount.add(msg.value);

        if (will >= InvoiceAmount) {
            if (will > InvoiceAmount)
                doRefund(will - InvoiceAmount);
            CurrentAmount = InvoiceAmount;
            WasPaid = true;
        }
        else
            CurrentAmount = will;

        emit Payment(msg.sender, msg.value);
    }

    function withdraw(address receiver, uint256 amount) public {
        Status status = getStatus();

        require(CurrentAmount >= amount);

        require (
            (status == Status.Paid && msg.sender == Beneficiary) ||
            (status == Status.Overdue && msg.sender == PartialReceiver)
        );

        doWithdraw(receiver, amount);

        CurrentAmount = CurrentAmount.sub(amount);
    }
}

