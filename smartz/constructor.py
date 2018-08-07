import time
from smartz.api.constructor_engine import ConstructorInstance


class Constructor(ConstructorInstance):

    def get_version(self):
        return {
            "result": "success",
            "version": 2,
            "blockchain": "ethereum"
        }

    def get_params(self):
        json_schema = {
            "type": "object",
            "required": [
                "invoiceAmount", "beneficiary", "memo"
            ],

            "additionalProperties": False,

            "properties": {
                "invoiceAmount": {
                    "title": "Invoice Amount",
                    "description": "Ether amount which should be paid.",
                    "$ref": "#/definitions/ethCount"
                },

                "beneficiary": {
                    "title": "Beneficiary address",
                    "description": "Who will get money when the invoice is paid.",
                    "$ref": "#/definitions/address"
                },

                "memo": {
                    "title": "Short message",
                    "description": "What is the invoice for.",
                    "type": "string",
                    "minLength": 0,
                    "maxLength": 256
                },

                "payer": {
                    "title": "Payer address",
                    "description": "If this address is set, invoice can be paid only from it. All other receipts will be returned.",
                    "$ref": "#/definitions/address"
                },

                "validityPeriod": {
                    "title": "Valid Until",
                    "description": "After this date invoice contract will not accept incoming Ether and will send it back.",
                    "$ref": "#/definitions/unixTime"
                },

                "partialReceiver": {
                    "title": "Partial Receiver",
                    "description": "Who will be able to withdraw funds from invoice contract after it validity period ends if partial funds accumulated but invoice amount is not collected.",
                    "type": "string",
                    "enum": ['Beneficiary', 'Payer'],
                }
            },

            "dependencies": {
                "validityPeriod": ["partialReceiver"]
            }
        }

        ui_schema = {
            "invoiceAmount": {
                "ui:widget": "ethCount",
            },
            "validityPeriod": {
                "ui:widget": "unixTime",
            },
            "partialReceiver": {
                "ui:widget": "radio",
            }
        }

        return {
            "result": "success",
            "schema": json_schema,
            "ui_schema": ui_schema
        }

    def construct(self, fields_vals):

        source = self.__class__._TEMPLATE

        if 'payer' not in fields_vals:
            fields_vals['payer'] = '0x00'
            source = source.replace('%payerVisibility%', 'internal')
        else:
            source = source.replace('%payerVisibility%', 'public')

        if 'validityPeriod' not in fields_vals:
            fields_vals['validityPeriod'] = 0
            source = source.replace('%validityPeriodVisibility%', 'internal')
            source = source.replace('%partialReceiverVisibility%', 'internal')
        else:
            source = source.replace('%validityPeriodVisibility%', 'public')
            source = source.replace('%partialReceiverVisibility%', 'public')

        if 'partialReceiver' not in fields_vals:
            fields_vals['partialReceiver'] = '0x00'
        elif fields_vals['partialReceiver'] == 'Beneficiary':
            fields_vals['partialReceiver'] = fields_vals['beneficiary']
        elif fields_vals['partialReceiver'] == 'Payer':
            fields_vals['partialReceiver'] = fields_vals['payer']
        else:
            return {
                "result": "error",
                "error_descr": "incorrect `partialReceiver`"
            }

        source = source \
            .replace('%invoiceAmount%', str(fields_vals['invoiceAmount'])) \
            .replace('%beneficiary%', fields_vals['beneficiary']) \
            .replace('%memo%', fields_vals['memo']) \
            .replace('%payer%', fields_vals['payer']) \
            .replace('%validityPeriod%', str(fields_vals['validityPeriod'])) \
            .replace('%partialReceiver%', fields_vals['partialReceiver'])

        return {
            "result": "success",
            'source': source,
            'contract_name': "InvoiceWrapper"
        }

    def post_construct(self, fields_vals, abi_array):

        function_titles = {
            'InvoiceAmount': {
                'title': 'Invoice Amount',
                'description': 'Ether amount which should be paid.',
                'ui:widget': 'ethCount',
                'sorting_order': 5
            },

            'CurrentAmount': {
                'title': 'Current Amount',
                'description': 'Ether amount currently accumulated in invoice.',
                'ui:widget': 'ethCount',
                'sorting_order': 10
            },

            'Beneficiary': {
                'title': 'Beneficiary',
                'description': 'Who will get money when the invoice is paid.',
                'sorting_order': 10
            },

            'Memo': {
                'title': 'Short Message',
                'description': 'What is the invoice for.',
                'sorting_order': 15
            },

            'ValidityPeriod': {
                'title': 'Valid Until',
                'description': 'After this date invoice contract will not accept incoming Ether and will send it back.',
                'ui:widget': 'unixTime',
                'ui:widget_options': {
                    'format': "yyyy.mm.dd HH:MM:ss (o)"
                },
                'sorting_order': 20
            },

            'Payer': {
                'title': 'Payer',
                'description': 'If this address is set, invoice can be paid only from it. All other receipts will be returned.',
                'sorting_order': 25
            },

            'PartialReceiver': {
                'title': 'Partial Receiver',
                'description': 'Who will be able to withdraw funds from invoice contract after it validity period ends if partial funds accumulated but invoice amount is not collected.',
                'sorting_order': 30
            },

            'Owner': {
                'title': 'Contract Owner',
                'description': 'Contract owner address.',
                'sorting_order': 35
            },

            'getStatus': {
                'title': 'Status',
                'description': 'Current invoice status',
                'ui:widget': 'enum',
                'ui:widget_options': {
                    'enum': ['Active', 'Overdue', 'Paid']
                },
                'sorting_order': 40
            },

            'pay': {
                'title': 'Pay invoice',
                'description': 'Pay the invoice',
                'payable_details': {
                    'title': 'Ether amount',
                    'description': 'This ether amount will be sent with the function call.'
                },
                'sorting_order': 45
            },

            'withdraw': {
                'title': 'Withdraw',
                'description': 'Withdraw funds from invoice contract after it validity period ends if partial funds accumulated but invoice amount is not collected.',
                'sorting_order': 50,
                'inputs': [{
                    'title': 'Receiver Address',
                    'description': 'Who will receive funds'
                }, {
                    'title': 'Ether Amount',
                    'description': 'This ether amount will be sent.',
                    'ui:widget': 'ethCount'
                }]
            }
        }

        return {
            "result": "success",
            'function_specs': function_titles,
            'dashboard_functions': ['InvoiceAmount', 'CurrentAmount', 'getStatus']
        }


    # language=Solidity
    _TEMPLATE = """
pragma solidity ^0.4.20;

library SafeMath {
  function mul(uint256 a, uint256 b) internal pure returns (uint256) {
    if (a == 0) {
      return 0;
    }
    uint256 c = a * b;
    assert(c / a == b);
    return c;
  }

  function div(uint256 a, uint256 b) internal pure returns (uint256) {
    // assert(b > 0); // Solidity automatically throws when dividing by 0
    uint256 c = a / b;
    // assert(a == b * c + a % b); // There is no case in which this doesn't hold
    return c;
  }

  function sub(uint256 a, uint256 b) internal pure returns (uint256) {
    assert(b <= a);
    return a - b;
  }

  function add(uint256 a, uint256 b) internal pure returns (uint256) {
    uint256 c = a + b;
    assert(c >= a);
    return c;
  }
}

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
    uint256 %validityPeriodVisibility% ValidityPeriod;
    address public Beneficiary;
    address %payerVisibility% Payer;
    address %partialReceiverVisibility% PartialReceiver;
    string public Memo;
    address internal Owner;

    bool internal WasPaid;

    function Invoice (
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
        Refund(msg.sender, amount);
    }

    function doWithdraw(address receiver, uint256 amount) internal {
        receiver.transfer(amount);
        Withdraw(receiver, amount);
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

        Payment(msg.sender, msg.value);
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

contract InvoiceWrapper is Invoice(
    %invoiceAmount%,
    "%memo%",
    %beneficiary%,
    %payer%,
    %validityPeriod%,
    %partialReceiver%
) { }
    """
