
#include <cstdint>
#include <type_traits>
#include <limits>

////////////////////////////////////////
//     Example 'define interface'     //
////////////////////////////////////////
#define __IO volatile

typedef struct {
    __IO uint32_t CR;
} I2C_TypeDef;

/******************  Bit definition for I2C_CR register  **********************/
#define I2C_CR_SADD_Pos              (0U)
#define I2C_CR_SADD_Msk              (0x3FFUL << I2C_CR_SADD_Pos)              /*!< 0x000003FF */
#define I2C_CR_SADD                  I2C_CR_SADD_Msk                           /*!< Slave address (master mode) */
#define I2C_CR_RD_WRN_Pos            (10U)
#define I2C_CR_RD_WRN_Msk            (0x1UL << I2C_CR_RD_WRN_Pos)              /*!< 0x00000400 */
#define I2C_CR_RD_WRN                I2C_CR_RD_WRN_Msk                         /*!< Transfer direction (master mode) */
#define I2C_CR_NBYTES_Pos            (16U)
#define I2C_CR_NBYTES_Msk            (0xFFUL << I2C_CR_NBYTES_Pos)             /*!< 0x00FF0000 */
#define I2C_CR_NBYTES                I2C_CR_NBYTES_Msk                         /*!< Number of bytes */
#define I2C_CR_PE_Pos                (31U)
#define I2C_CR_PE_Msk                (0x1UL << I2C_CR_PE_Pos)                  /*!< 0x80000000 */
#define I2C_CR_PE                    I2C_CR_PE_Msk                             /*!< Peripheral enable */

////////////////////////////////////////
//  Example 'C++ accessor functions'  //
////////////////////////////////////////
// Please note that all below code would normally be auto-generated and there would be no need to look at it.
//
template <typename Treg, typename Tval, unsigned int Offset, unsigned int Width>
struct BaseField {
    // Define some useful field attributes
    using reg_type = typename std::remove_reference_t<Treg>::reg_type;
    static auto const reg_bits = std::numeric_limits<reg_type>::digits;

    // Define mask for this field
    static_assert(Width > 0, "Width must be non-zero");
    static_assert((Offset + Width) <= reg_bits, "Offset + Width must not exceed reg_type value size");
    static reg_type const constexpr Mask = (((Offset + Width) == reg_bits) ? 0 : (reg_type(1) << (Offset + Width))) - (1U << Offset);

    // Create accessors for underlying data of this field
    Treg& reg_;
    Tval& val_;

  protected:
    // Modify functions are internal, exposed with different signature by either VolatileField or StableField
    template <typename Targ, class = typename std::enable_if<std::is_integral<Targ>::value>::type>
    void mod_internal(Targ val_set, typename std::enable_if_t<std::is_integral_v<Targ>>* = 0) {
        if (__builtin_constant_p(val_set)) {
            // Constant input, write value to fold to immediate instruction
            val_ = (val_ & ~Mask) | ((val_set << Offset) & Mask);
            return;
        }
        // Force use BFI instruction
#if defined(__ARM_ARCH_ISA_A64) && __ARM_ARCH_ISA_A64
        if (reg_bits > 32) {
            asm (
            // More than 32 bits, use X type register
                "bfi     %x[res], %x[set], %[off], %[len]"
                : [res]"=r" (val_)
                :       "r" (val_),
                  [set] "r" (val_set), [off]"i" (Offset), [len]"i" (Width)
            );
        } else
#endif
        {
            asm (
#if defined(__ARM_ARCH_ISA_A64) && __ARM_ARCH_ISA_A64
            // Use W type register on 64-bit systems
                "bfi     %w[res], %w[set], %[off], %[len]"
#else
            // Use any register on 32-bit systems
                "bfi     %[res], %[set], %[off], %[len]"
#endif
                : [res]"=r" (val_)
                :       "r" (val_),
                  [set] "r" (val_set), [off]"i" (Offset), [len]"i" (Width)
            );
        }
    }

    void set_internal() {
        val_ |= Mask;
    }
    void clr_internal() {
        val_ &= ~Mask;
    }

  public:
    // Read access functions for this field
    template <typename Tauto>
    operator Tauto() const {
        static_assert((not std::is_same_v<Tauto, bool>) || (Width == 1), "Boolean return value is only valid for single bit fields");
        static_assert(std::numeric_limits<Tauto>::digits >= Width, "Destination type too small, use an explicit cast to discard additional bits");
        return (val_ & Mask) >> Offset;
    }
    auto get() const {
        if constexpr (Width == 1) {
            // For auto values of width 1, automatically convert to boolean
            return static_cast<bool>(this->operator reg_type());
        } else {
            // For other widths, use the register type
            return this->operator reg_type();
        }
    }

  private:
    // Delete unwanted operators
    BaseField(BaseField const&) = delete;
    BaseField& operator=(BaseField const&) = delete;
};

// Specialization of BaseField with RMW (volatile) access
template <typename Treg, unsigned int Offset, unsigned int Width>
struct VolatileField : public BaseField<Treg, volatile typename std::remove_reference_t<Treg>::reg_type, Offset, Width> {
    using Base = BaseField<Treg, volatile typename std::remove_reference_t<Treg>::reg_type, Offset, Width>;

    // Expose as RMW, since access is volatile, it implicitly performs a read and write
    template <typename Targ, class = typename std::enable_if<std::is_integral<Targ>::value>::type>
    void rmw(Targ val_set, typename std::enable_if_t<std::is_integral_v<Targ>>* = 0) {
        Base::mod_internal(val_set);
    }
    template <typename Targ>
    void rmw(Targ val_set, typename std::enable_if_t<!std::is_integral_v<Targ> && std::is_enum_v<Targ>>* = 0) {
        rmw(static_cast<std::underlying_type_t<Targ>>(val_set));
    }

    // Do not return reg_, call chaining is ill-advised
    void set() {
        Base::set_internal();
    }
    void clr() {
        Base::clr_internal();
    }
};

// Specialization of BaseField with modify-only (non-volatile) access
template <typename Treg, unsigned int Offset, unsigned int Width>
struct StableField : public BaseField<Treg, typename std::remove_reference_t<Treg>::reg_type, Offset, Width> {
    using Base = BaseField<Treg, typename std::remove_reference_t<Treg>::reg_type, Offset, Width>;
    
    // Expose as modify-only, no implicit read or write is performed
    template <typename Targ>
    auto& mod(Targ val_set, typename std::enable_if_t<std::is_integral_v<Targ>>* = 0) {
        Base::mod_internal(val_set);
        return Base::reg_;
    }
    template <typename Targ>
    auto& mod(Targ val_set, typename std::enable_if_t<!std::is_integral_v<Targ> && std::is_enum_v<Targ>>* = 0) {
        return mod(static_cast<std::underlying_type_t<Targ>>(val_set));
    }

    // Stable call chaining is desired, return reg_
    auto& set() {
        Base::set_internal();
        return Base::reg_;
    }
    auto& clr() {
        Base::clr_internal();
        return Base::reg_;
    }
};

template <typename Tval, typename Reg>
struct Register {
    using reg_type = Tval;
    volatile Tval val_vol;
    
    auto read() {
        return typename Reg::StableAccess{val_vol, val_vol};
    }
    auto init(Tval val_init) {
        return typename Reg::StableAccess{val_vol, val_init};
    }
    void write(Tval val_write) {
        val_vol = val_write;
    }
    void clear() {
        val_vol = 0;
    }

  private:
    // Delete unwanted operators
    Register(Register const&) = delete;
    Register& operator=(Register const&) = delete;
};

template <typename Tval>
struct StableAccessBase {
    using reg_type = Tval;
    volatile Tval& val_vol;
    Tval val_copy;

    operator Tval() {
        return val_copy;
    }
    void write() {
        val_vol = val_copy;
    }

  private:
    // Delete unwanted operators
    StableAccessBase(StableAccessBase const&) = delete;
    StableAccessBase& operator=(StableAccessBase const&) = delete;
};

////////////////////////////////////////
//      Example 'C++ interface'       //
////////////////////////////////////////
struct I2cInterface {
    struct _CR : public Register<std::uint32_t, _CR> {
        auto SADD() { return VolatileField<decltype(*this), 0, 10>{*this, val_vol}; }
        auto RD_WRN() { return VolatileField<decltype(*this), 10, 1>{*this, val_vol}; }
        auto NBYTES() { return VolatileField<decltype(*this), 16, 8>{*this, val_vol}; }
        auto PE() { return VolatileField<decltype(*this), 31, 1>{*this, val_vol}; }

        struct StableAccess : public StableAccessBase<reg_type> {
            auto SADD() { return StableField<decltype(*this), 0, 10>{*this, val_copy}; }
            template <typename Targ> auto& SADD(Targ val) { return SADD().mod(val); }

            auto RD_WRN() { return StableField<decltype(*this), 10, 1>{*this, val_copy}; }
            template <typename Targ> auto& RD_WRN(Targ val) { return RD_WRN().mod(val); }

            auto NBYTES() { return StableField<decltype(*this), 16, 8>{*this, val_copy}; }
            template <typename Targ> auto& NBYTES(Targ val) { return NBYTES().mod(val); }

            auto PE() { return StableField<decltype(*this), 31, 1>{*this, val_copy}; }
            template <typename Targ> auto& PE(Targ val) { return PE().mod(val); }
        };
    } CR;
};
// This static assertion proves that all the accessor functions constitute no data, and thus they can be mapped on the actual register address
static_assert(sizeof(I2cInterface) == sizeof(I2C_TypeDef), "Too many data members");

////////////////////////////////////////
// Example code for old and new infcs //
////////////////////////////////////////
std::uint32_t i2c_transmit(I2C_TypeDef& i2c, std::uint8_t address, std::uint16_t length) {
    // Set the Peripheral Enable bit first to allow further access
    i2c.CR |= I2C_CR_PE;

    // Read-Modify-Write cycle to efficiently configure the required fields
    auto cr = i2c.CR;                                                                       // Read register once
    cr = (cr & ~I2C_CR_SADD_Msk) | ((address << I2C_CR_SADD_Pos) & I2C_CR_SADD_Msk);        // Modify address
    cr = (cr & ~I2C_CR_NBYTES_Msk) | ((length << I2C_CR_NBYTES_Pos) & I2C_CR_NBYTES_Msk);   // Modify number of bytes
    cr &= ~I2C_CR_RD_WRN;                                                                   // Clear RD_WRN for transmit
    i2c.CR = cr;                                                                            // Write result to register

    // Retrieve the SADD value
    return (i2c.CR & I2C_CR_NBYTES_Msk) >> I2C_CR_NBYTES_Pos;
}

std::uint32_t i2c_transmit(I2cInterface& i2c, std::uint8_t address, std::uint16_t length) {
    // Set the Peripheral Enable bit first to allow further access
    i2c.CR.PE().set();

    // Read-Modify-Write cycle to efficiently configure the required fields
    i2c.CR.read()       // Read register once
       .SADD(address)   // Modify address (shorthand for cr.SADD().mod(address))
       .NBYTES(length)  // Modify number of bytes (shorthand for cr.NBYTES().mod(length))
       .RD_WRN().clr()  // Clear RD_WRN for transmit (explicit way of writing RD_WRN(0))
       .write();        // Write result to register (shorthand for i2c.cr.write(cr))

    // Retrieve the SADD value
    auto val = i2c.CR.NBYTES();
    return i2c.CR.NBYTES().get();
}
