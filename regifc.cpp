
#include <cstdint>

////////////////////////////////////////
//      Example 'old interface'       //
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
//      Example 'new interface'       //
////////////////////////////////////////
// Please note that all below code would normally be auto-generated and there would be no need to look at it.
// 
template <std::uint32_t Offset, std::uint32_t Length>
struct VolatileMask {
    static_assert(Length > 0, "Length must be non-zero");
    static_assert((Offset + Length) <= 32, "Offset + Length must not exceed 32 bit value size");
    static std::uint32_t const constexpr Mask = (Offset + Length == 32 ? 0 : (1U << (Offset + Length))) - (1U << Offset);

    volatile std::uint32_t& val_;
    void rmw(std::uint32_t val_set) {
#if not defined(__GNUC__) || defined(__clang__)
        // TODO: also clang seems to mess up sometimes, always use BFI for clang as well?
        // But, if not available, BFI needs to not be used...
        rmw_internal(val_set);
#else
        // Note, GCC does not properly optimize rmw_internal for non-set/clr functions
        // Instead, immediately inject the optimized bfi instruction, the assembly is equivalent
        asm (
            "bfi     %[res], %[set], %[off], %[len]"
            : [res]"=r" (val_)
            :       "r" (val_),
              [set]"r" (val_set), [off]"i" (Offset), [len]"i" (Length)
        );
#endif
    }

    void set() {
        // TODO: use bitbanding if available and length == 1
        val_ |= Mask;
    }

    void clr() {
        // TODO: use bitbanding if available and length == 1
        val_ &= ~Mask;
    }

  protected:
    void rmw_internal(std::uint32_t val_set) {
        val_ = (val_ & ~Mask) | ((val_set << Offset) & Mask);
    }
};

template <std::uint32_t Offset, std::uint32_t Length>
struct StableMask {
    static_assert(Length > 0, "Length must be non-zero");
    static_assert((Offset + Length) <= 32, "Offset + Length must not exceed 32 bit value size");
    static std::uint32_t const constexpr Mask = (Offset + Length == 32 ? 0 : (1U << (Offset + Length))) - (1U << Offset);

    std::uint32_t& val_;
    void mod(std::uint32_t val_set) {
#if not defined(__GNUC__) || defined(__clang__)
        // TODO: also clang seems to mess up sometimes, always use BFI for clang as well?
        // But, if not available, BFI needs to not be used...
        mod_internal(val_set);
#else
        // Note, GCC does not properly optimize rmw_internal for non-set/clr functions
        // Instead, immediately inject the optimized bfi instruction, the assembly is equivalent
        asm (
            "bfi     %[res], %[set], %[off], %[len]"
            : [res]"=r" (val_)
            :       "r" (val_),
              [set]"r" (val_set), [off]"i" (Offset), [len]"i" (Length)
        );
#endif
    }

    void set() {
        // TODO: use bitbanding if available and length == 1
        val_ |= Mask;
    }

    void clr() {
        // TODO: use bitbanding if available and length == 1
        val_ &= ~Mask;
    }

  protected:
    void mod_internal(std::uint32_t val_set) {
        val_ = (val_ & ~Mask) | ((val_set << Offset) & Mask);
    }
};

template <std::uint32_t Offset>
struct VolatileFlag : public VolatileMask<Offset, 1> {
};

template <std::uint32_t Offset>
struct StableFlag : public StableMask<Offset, 1> {
};

#define I2C_CR_PE_Pos                (31U)
#define I2C_CR_PE_Msk                (0x1UL << I2C_CR_PE_Pos)                  /*!< 0x80000000 */
#define I2C_CR_PE                    I2C_CR_PE_Msk                             /*!< Peripheral enable */
struct I2cInterface {
    struct Cr {
        volatile std::uint32_t val_;

        auto sadd() {
            return VolatileMask<0, 10>{val_};
        }

        auto rd_wrn() {
            return VolatileFlag<10>{val_};
        }

        auto nbytes() {
            return VolatileMask<16, 8>{val_};
        }

        auto pe() {
            return VolatileFlag<31>{val_};
        }

        struct Access {
            volatile std::uint32_t& val_;
            std::uint32_t val_copy;

            void write() {
                val_ = val_copy;
            }

            auto sadd() {
                return StableMask<0, 10>{val_copy};
            }

            auto rd_wrn() {
                return StableFlag<10>{val_copy};
            }

            auto nbytes() {
                return StableMask<16, 8>{val_copy};
            }

            auto pe() {
                return StableFlag<31>{val_copy};
            }
        };

        Access read() {
            return Access{val_, val_};
        }

        void write(std::uint32_t val_write) {
            val_ = val_write;
        }
        void write(Access const& access) {
            val_ = access.val_copy;
        }
    } cr;
};
static_assert(sizeof(I2cInterface) == sizeof(I2C_TypeDef), "Too many data members");


////////////////////////////////////////
// Example code for old and new infc  //
////////////////////////////////////////
void __attribute__((noreturn)) i2c_transmit(I2C_TypeDef& i2c, std::uint8_t address, std::uint16_t length) {
    // Set the Peripheral Enable bit first to allow further access
    i2c.CR |= I2C_CR_PE;

    // Read-Modify-Write cycle to efficiently configure the required fields
    auto cr = i2c.CR;                                                                       // Read register once
    cr = (cr & ~I2C_CR_SADD_Msk) | ((address << I2C_CR_SADD_Pos) & I2C_CR_SADD_Msk);        // Modify address
    cr = (cr & ~I2C_CR_NBYTES_Msk) | ((length << I2C_CR_NBYTES_Pos) & I2C_CR_NBYTES_Msk);   // Modify number of bytes
    cr &= ~I2C_CR_RD_WRN;                                                                   // Clear RD_WRN for transmit
    i2c.CR = cr;                                                                            // Write result to register
}

void __attribute__((noreturn)) i2c_transmit(I2cInterface& i2c, std::uint8_t address, std::uint16_t length) {
    // Set the Peripheral Enable bit first to allow further access
    i2c.cr.pe().set();

    // Read-Modify-Write cycle to efficiently configure the required fields
    auto cr = i2c.cr.read();    // Read register once
    cr.sadd().mod(address);     // Modify address
    cr.nbytes().mod(length);    // Modify number of bytes
    cr.rd_wrn().clr();          // Clear RD_WRN for transmit (shorthand for cr.rd_wrn().mod(0))
    cr.write();                 // Write result to register (shorthand for i2c.cr.write(cr))
}


